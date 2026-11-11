"""
Multi-Model LLM Orchestration and Zero-Downtime 3-Tier Fallback Engine.

Built on LangChain (`langchain-openai` + `langchain-core`) targeting OpenRouter:
- Tier 1 (Primary): `nvidia/nemotron-3-ultra-550b-a55b:free` (Nemotron 3 Ultra; reasoning traces extracted when returned)
- Tier 2 (Fallback): `nvidia/nemotron-3.5-super-vl:free` (Nemotron 3.5 Super VL; rate limit / timeout / API error fallback)
- Tier 3 (Offline / Deterministic Heuristics): Local deterministic fallback when API keys are missing/mock or network fails.
"""

from __future__ import annotations

import json
import logging
import re
from enum import StrEnum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Gemini-style <thought> and the <think> tags used by Nemotron and other reasoning models.
_THOUGHT_PATTERN = re.compile(r"<(?:thought|think)>(.*?)</(?:thought|think)>", re.IGNORECASE | re.DOTALL)
_JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class OrchestrationTier(StrEnum):
    """Execution tier that produced an agent decision."""

    TIER_1_GEMINI_THINKING = "TIER_1_GEMINI_THINKING"
    TIER_2_LLAMA_70B = "TIER_2_LLAMA_70B"
    TIER_3_DETERMINISTIC_HEURISTIC = "TIER_3_DETERMINISTIC_HEURISTIC"


class LLMArbitrationPayload(BaseModel):
    """Structured payload parsed from Tier 1 / Tier 2 LLM output."""

    win_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    executive_summary: str | None = None
    rebuttal_statement: str | None = None
    customer_message: str | None = None
    evidence_citations: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)


class LLMOrchestrationResult(BaseModel):
    """Result envelope returned by MultiModelLLMOrchestrator."""

    tier_used: OrchestrationTier
    model_name: str
    payload: LLMArbitrationPayload | None = None
    thought_trace: str | None = None
    extracted_reasoning_steps: list[str] = Field(default_factory=list)
    fallback_reasons: list[str] = Field(default_factory=list)


class MultiModelLLMOrchestrator:
    """Three-tier resilient LangChain orchestrator with OpenRouter primary/fallback and offline heuristics."""

    def __init__(
        self,
        settings: Settings | None = None,
        primary_llm: Any | None = None,
        fallback_llm: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._primary_llm = primary_llm
        self._fallback_llm = fallback_llm

    def has_live_credentials(self) -> bool:
        """Return True when a real (non-mock) OpenRouter API key is configured."""
        key = (self.settings.OPENROUTER_API_KEY or "").strip()
        if not key:
            return False
        lowered = key.lower()
        return not (
            lowered.startswith("mock")
            or lowered.startswith("replace")
            or lowered in ("changeme", "test", "none", "null")
        )

    def _build_openrouter_chat_model(self, model_name: str, temperature: float = 0.1) -> ChatOpenAI:
        """Construct a LangChain ChatOpenAI client targeting OpenRouter."""
        return ChatOpenAI(
            model=model_name,
            api_key=self.settings.OPENROUTER_API_KEY,  # type: ignore[arg-type]
            base_url=self.settings.OPENROUTER_BASE_URL,
            temperature=temperature,
            timeout=self.settings.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=0,
            default_headers={
                "HTTP-Referer": self.settings.OPENROUTER_SITE_URL,
                "X-Title": self.settings.OPENROUTER_APP_NAME,
            },
        )

    def _get_primary_llm(self) -> Any:
        if self._primary_llm is None:
            self._primary_llm = self._build_openrouter_chat_model(
                self.settings.OPENROUTER_PRIMARY_MODEL
            )
        return self._primary_llm

    def _get_fallback_llm(self) -> Any:
        if self._fallback_llm is None:
            self._fallback_llm = self._build_openrouter_chat_model(
                self.settings.OPENROUTER_FALLBACK_MODEL
            )
        return self._fallback_llm

    @staticmethod
    def extract_thought_trace(raw_text: str) -> tuple[str | None, str]:
        """
        Extract `<thought>...</thought>` chain-of-thought blocks from Gemini Thinking output.
        Returns (combined_thought_trace, remaining_content_without_thought_tags).
        """
        matches = [m.strip() for m in _THOUGHT_PATTERN.findall(raw_text) if m.strip()]
        cleaned = _THOUGHT_PATTERN.sub("", raw_text).strip()
        if not matches:
            return None, cleaned
        return "\n".join(matches), cleaned

    @staticmethod
    def thought_trace_to_steps(thought_trace: str | None) -> list[str]:
        """Convert raw `<thought>` trace into clean structured reasoning_steps."""
        if not thought_trace:
            return []
        steps: list[str] = []
        for raw_line in thought_trace.splitlines():
            line = raw_line.strip().lstrip("-*•").strip()
            if line:
                steps.append(f"[Thought] {line}")
        return steps

    @staticmethod
    def parse_structured_payload(text_content: str) -> LLMArbitrationPayload:
        """Parse JSON arbitration output from raw text or fenced markdown JSON."""
        candidate = text_content.strip()
        fence_match = _JSON_FENCE_PATTERN.search(candidate)
        if fence_match:
            candidate = fence_match.group(1).strip()
        else:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = candidate[start : end + 1]

        parsed = json.loads(candidate)
        return LLMArbitrationPayload.model_validate(parsed)

    @staticmethod
    def _extract_response_text_and_thought(response: Any) -> tuple[str, str | None]:
        """Extract raw string content and optional OpenRouter reasoning metadata from LangChain AIMessage."""
        content = getattr(response, "content", response)
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            raw_text = "\n".join(parts)
        else:
            raw_text = str(content)

        extra_thought: str | None = None
        additional_kwargs = getattr(response, "additional_kwargs", None) or {}
        if isinstance(additional_kwargs, dict):
            reasoning = additional_kwargs.get("reasoning_content") or additional_kwargs.get(
                "reasoning"
            )
            if isinstance(reasoning, str) and reasoning.strip():
                extra_thought = reasoning.strip()

        return raw_text, extra_thought

    async def invoke_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        allow_live_when_mock_client: bool = False,
    ) -> LLMOrchestrationResult:
        """
        Execute 3-tier resilient LLM invocation:
        Tier 1 (Gemini 2.0 Flash Thinking) -> Tier 2 (Llama 3.3 70B) -> Tier 3 (Deterministic Heuristics).
        """
        fallback_reasons: list[str] = []
        has_injected_clients = self._primary_llm is not None or self._fallback_llm is not None

        if not self.has_live_credentials() and not (
            allow_live_when_mock_client and has_injected_clients
        ):
            reason = "No live OpenRouter API key configured; routing directly to Tier 3 deterministic heuristics."
            logger.debug(reason)
            return LLMOrchestrationResult(
                tier_used=OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC,
                model_name="deterministic-rule-engine",
                payload=None,
                fallback_reasons=[reason],
            )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Tier 1: OpenRouter Google Gemini 2.0 Flash Thinking
        try:
            primary_llm = self._get_primary_llm()
            response = await primary_llm.ainvoke(messages)
            raw_text, extra_thought = self._extract_response_text_and_thought(response)
            tag_thought, cleaned_text = self.extract_thought_trace(raw_text)
            combined_thought = "\n".join(p for p in (extra_thought, tag_thought) if p) or None
            payload = self.parse_structured_payload(cleaned_text)
            thought_steps = self.thought_trace_to_steps(combined_thought)
            merged_steps = thought_steps + [
                s for s in payload.reasoning_steps if s not in thought_steps
            ]
            return LLMOrchestrationResult(
                tier_used=OrchestrationTier.TIER_1_GEMINI_THINKING,
                model_name=self.settings.OPENROUTER_PRIMARY_MODEL,
                payload=payload,
                thought_trace=combined_thought,
                extracted_reasoning_steps=merged_steps,
                fallback_reasons=[],
            )
        except Exception as exc:
            msg = f"Tier 1 ({self.settings.OPENROUTER_PRIMARY_MODEL}) failed: {exc}"
            logger.warning(msg)
            fallback_reasons.append(msg)

        # Tier 2: OpenRouter Meta Llama 3.3 70B Instruct
        try:
            fallback_llm = self._get_fallback_llm()
            response = await fallback_llm.ainvoke(messages)
            raw_text, extra_thought = self._extract_response_text_and_thought(response)
            tag_thought, cleaned_text = self.extract_thought_trace(raw_text)
            combined_thought = "\n".join(p for p in (extra_thought, tag_thought) if p) or None
            payload = self.parse_structured_payload(cleaned_text)
            thought_steps = self.thought_trace_to_steps(combined_thought)
            merged_steps = thought_steps + [
                s for s in payload.reasoning_steps if s not in thought_steps
            ]
            return LLMOrchestrationResult(
                tier_used=OrchestrationTier.TIER_2_LLAMA_70B,
                model_name=self.settings.OPENROUTER_FALLBACK_MODEL,
                payload=payload,
                thought_trace=combined_thought,
                extracted_reasoning_steps=merged_steps,
                fallback_reasons=fallback_reasons,
            )
        except Exception as exc:
            msg = f"Tier 2 ({self.settings.OPENROUTER_FALLBACK_MODEL}) failed: {exc}"
            logger.warning(msg)
            fallback_reasons.append(msg)

        # Tier 3: Deterministic Offline Heuristics
        fallback_reasons.append(
            "Both Tier 1 and Tier 2 OpenRouter models unavailable; utilizing Tier 3 deterministic heuristics."
        )
        return LLMOrchestrationResult(
            tier_used=OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC,
            model_name="deterministic-rule-engine",
            payload=None,
            fallback_reasons=fallback_reasons,
        )
