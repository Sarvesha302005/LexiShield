"""
Multi-Model LLM Orchestration and Zero-Downtime Fallback Engine.

Built on LangChain (`langchain-openai` + `langchain-core`) against OpenAI-compatible providers.
With an NVIDIA NIM key configured, each purpose has its own chain:
- Analysis (dispute decisions, formal rebuttal): Nemotron 3.5 Super VL -> Nemotron 3.5 Lightning
- Chat (merchant replies, simulated buyer): Nemotron 3.5 Bolt -> Nemotron 3.5 Lightning
- Backup for both: OpenRouter `nvidia/nemotron-3.5-super-vl:free`, a second provider for NIM outages
Without an NVIDIA key, OpenRouter serves Tier 1 and Tier 2 (OPENROUTER_PRIMARY_MODEL / _FALLBACK_MODEL).
- Tier 3 (Offline / Deterministic Heuristics): used when no key is configured or every model fails.
"""

from __future__ import annotations

import json
import logging
import re
from enum import StrEnum
from typing import Any, NamedTuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Gemini-style <thought> and the <think> tags used by Nemotron and other reasoning models.
_THOUGHT_PATTERN = re.compile(
    r"<(?:thought|think)>(.*?)</(?:thought|think)>", re.IGNORECASE | re.DOTALL
)
_JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class OrchestrationTier(StrEnum):
    """Execution tier that produced an agent decision."""

    TIER_1_GEMINI_THINKING = "TIER_1_GEMINI_THINKING"
    TIER_2_LLAMA_70B = "TIER_2_LLAMA_70B"
    OPENROUTER_BACKUP = "OPENROUTER_BACKUP"
    TIER_3_DETERMINISTIC_HEURISTIC = "TIER_3_DETERMINISTIC_HEURISTIC"


# Human-readable names for log and fallback messages.
_TIER_LABELS = {
    OrchestrationTier.TIER_1_GEMINI_THINKING: "Tier 1",
    OrchestrationTier.TIER_2_LLAMA_70B: "Tier 2",
    OrchestrationTier.OPENROUTER_BACKUP: "Backup",
}


class ModelRoute(NamedTuple):
    """One model to try, in order."""

    tier: OrchestrationTier
    provider: str  # "nvidia" or "openrouter"
    model_name: str


def _is_live_key(key: str | None) -> bool:
    """True for a real key; False for empty values and placeholders like 'mock_...'."""
    lowered = (key or "").strip().lower()
    if not lowered:
        return False
    return not (
        lowered.startswith("mock")
        or lowered.startswith("replace")
        or lowered in ("changeme", "test", "none", "null")
    )


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
    """Resilient LangChain orchestrator: NVIDIA NIM and/or OpenRouter models, then offline heuristics."""

    def __init__(
        self,
        settings: Settings | None = None,
        primary_llm: Any | None = None,
        fallback_llm: Any | None = None,
        purpose: str = "analysis",
    ) -> None:
        """`purpose` picks the NIM model chain: "analysis" (quality first) or "chat" (speed first)."""
        self.settings = settings or get_settings()
        self.purpose = purpose
        self._primary_llm = primary_llm
        self._fallback_llm = fallback_llm
        self._clients: dict[tuple[str, str], Any] = {}

    def has_live_credentials(self) -> bool:
        """Return True when a real (non-mock) NVIDIA NIM or OpenRouter API key is configured."""
        return self._nvidia_is_live() or self._openrouter_is_live()

    def _nvidia_is_live(self) -> bool:
        return _is_live_key(self.settings.NVIDIA_API_KEY)

    def _openrouter_is_live(self) -> bool:
        return _is_live_key(self.settings.OPENROUTER_API_KEY)

    def model_routes(self) -> list[ModelRoute]:
        """Models to try, in order. NVIDIA NIM serves Tier 1/2 when configured, with OpenRouter as backup."""
        s = self.settings
        if self._nvidia_is_live():
            if self.purpose == "chat":
                primary, fallback = s.NVIDIA_CHAT_PRIMARY_MODEL, s.NVIDIA_CHAT_FALLBACK_MODEL
            else:
                primary, fallback = s.NVIDIA_PRIMARY_MODEL, s.NVIDIA_FALLBACK_MODEL
            routes = [
                ModelRoute(OrchestrationTier.TIER_1_GEMINI_THINKING, "nvidia", primary),
                ModelRoute(OrchestrationTier.TIER_2_LLAMA_70B, "nvidia", fallback),
            ]
            if self._openrouter_is_live():
                routes.append(
                    ModelRoute(
                        OrchestrationTier.OPENROUTER_BACKUP, "openrouter", s.OPENROUTER_BACKUP_MODEL
                    )
                )
            return routes
        return [
            ModelRoute(
                OrchestrationTier.TIER_1_GEMINI_THINKING, "openrouter", s.OPENROUTER_PRIMARY_MODEL
            ),
            ModelRoute(
                OrchestrationTier.TIER_2_LLAMA_70B, "openrouter", s.OPENROUTER_FALLBACK_MODEL
            ),
        ]

    def _build_chat_model(self, route: ModelRoute, temperature: float = 0.1) -> ChatOpenAI:
        """Construct a LangChain ChatOpenAI client for the route's provider."""
        if route.provider == "nvidia":
            return ChatOpenAI(
                model=route.model_name,
                api_key=self.settings.NVIDIA_API_KEY,  # type: ignore[arg-type]
                base_url=self.settings.NVIDIA_BASE_URL,
                temperature=temperature,
                timeout=(
                    self.settings.NVIDIA_CHAT_TIMEOUT_SECONDS
                    if self.purpose == "chat"
                    else self.settings.NVIDIA_TIMEOUT_SECONDS
                ),
                max_retries=0,
            )
        return ChatOpenAI(
            model=route.model_name,
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

    def _llm_for(self, index: int, route: ModelRoute) -> Any:
        """Client for a route; injected test clients stand in for the first two routes."""
        if index == 0 and self._primary_llm is not None:
            return self._primary_llm
        if index == 1 and self._fallback_llm is not None:
            return self._fallback_llm
        key = (route.provider, route.model_name)
        if key not in self._clients:
            self._clients[key] = self._build_chat_model(route)
        return self._clients[key]

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

    async def _ainvoke_nonempty(self, llm: Any, messages: list[Any]) -> Any:
        """
        Invokes the model, retrying when it returns empty content. Some free providers (OpenRouter,
        NVIDIA NIM) intermittently answer with an empty message; a quick retry usually succeeds, which keeps the
        request on this tier instead of dropping to the next one.
        """
        attempts = max(1, self.settings.LLM_EMPTY_RESPONSE_ATTEMPTS)
        response = None
        for attempt in range(1, attempts + 1):
            response = await llm.ainvoke(messages)
            raw_text, _ = self._extract_response_text_and_thought(response)
            if raw_text.strip():
                return response
            logger.info(f"Model returned empty content (attempt {attempt}/{attempts}); retrying.")
        return response

    async def invoke_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        allow_live_when_mock_client: bool = False,
    ) -> LLMOrchestrationResult:
        """
        Tries each configured model in order (see model_routes) and returns the first parseable answer.
        Falls back to Tier 3 deterministic heuristics when no key is configured or every model fails.
        """
        fallback_reasons: list[str] = []
        has_injected_clients = self._primary_llm is not None or self._fallback_llm is not None

        if not self.has_live_credentials() and not (
            allow_live_when_mock_client and has_injected_clients
        ):
            reason = (
                "No live NVIDIA NIM or OpenRouter API key configured; "
                "routing directly to Tier 3 deterministic heuristics."
            )
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

        for index, route in enumerate(self.model_routes()):
            try:
                llm = self._llm_for(index, route)
                response = await self._ainvoke_nonempty(llm, messages)
                raw_text, extra_thought = self._extract_response_text_and_thought(response)
                tag_thought, cleaned_text = self.extract_thought_trace(raw_text)
                combined_thought = "\n".join(p for p in (extra_thought, tag_thought) if p) or None
                payload = self.parse_structured_payload(cleaned_text)
                thought_steps = self.thought_trace_to_steps(combined_thought)
                merged_steps = thought_steps + [
                    s for s in payload.reasoning_steps if s not in thought_steps
                ]
                return LLMOrchestrationResult(
                    tier_used=route.tier,
                    model_name=route.model_name,
                    payload=payload,
                    thought_trace=combined_thought,
                    extracted_reasoning_steps=merged_steps,
                    fallback_reasons=fallback_reasons,
                )
            except Exception as exc:
                msg = f"{_TIER_LABELS[route.tier]} ({route.model_name} via {route.provider}) failed: {exc}"
                logger.warning(msg)
                fallback_reasons.append(msg)

        # Tier 3: Deterministic Offline Heuristics
        fallback_reasons.append(
            "All configured LLM models unavailable; utilizing Tier 3 deterministic heuristics."
        )
        return LLMOrchestrationResult(
            tier_used=OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC,
            model_name="deterministic-rule-engine",
            payload=None,
            fallback_reasons=fallback_reasons,
        )
