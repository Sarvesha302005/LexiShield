"""
Unit tests for 3-Tier OpenRouter Multi-Model LLM Orchestration & Zero-Downtime Fallback.
Tests Tier 1 (Gemini 2.0 Flash Thinking + <thought> extraction),
Tier 2 (Meta Llama 3.3 70B fallback), and Tier 3 (Deterministic Heuristics).
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import SpecialistContext
from src.agents.inr_agent import INRAgent
from src.core.config import Settings
from src.models.schemas import (
    CarrierTrackingInfo,
    DisputeReason,
    DisputeStage,
    Money,
    OrderCustomerInfo,
    PayPalDisputeResource,
    WarehouseFulfillmentInfo,
)
from src.services.compliance import SellerProtectionComplianceEngine
from src.services.llm_orchestrator import MultiModelLLMOrchestrator, OrchestrationTier


def _make_ai_msg(content: str, additional_kwargs: dict | None = None):
    msg = MagicMock()
    msg.content = content
    msg.additional_kwargs = additional_kwargs or {}
    return msg


@pytest.mark.asyncio
async def test_tier1_gemini_thinking_extracts_thought_trace():
    """Tier 1 Gemini 2.0 Flash Thinking returns <thought> trace that populates reasoning_steps."""
    llm_json = json.dumps(
        {
            "win_probability": 0.94,
            "executive_summary": "Carrier delivery and signature satisfy PayPal §11.",
            "rebuttal_statement": "Formal §11 rebuttal invoking verified signature and GPS.",
            "customer_message": None,
            "evidence_citations": ["UPS Tracking delivered with signature."],
            "reasoning_steps": ["Verified Safe Harbor §11 compliance."],
        }
    )
    raw_output = (
        "<thought>\n"
        "- Verified carrier status == DELIVERED.\n"
        "- Confirmed GPS coordinates within delivery radius.\n"
        "</thought>\n"
        f"```json\n{llm_json}\n```"
    )

    primary = MagicMock()
    primary.ainvoke = AsyncMock(return_value=_make_ai_msg(raw_output))
    fallback = MagicMock()
    fallback.ainvoke = AsyncMock()

    settings = Settings(OPENROUTER_API_KEY="sk-or-live-test-key", ENVIRONMENT="test")
    orchestrator = MultiModelLLMOrchestrator(
        settings=settings, primary_llm=primary, fallback_llm=fallback
    )

    res = await orchestrator.invoke_with_fallback("system", "user")

    assert res.tier_used == OrchestrationTier.TIER_1_GEMINI_THINKING
    assert res.model_name == settings.OPENROUTER_PRIMARY_MODEL
    assert res.thought_trace is not None
    assert "Verified carrier status == DELIVERED." in res.thought_trace
    assert any("[Thought] Verified carrier status" in s for s in res.extracted_reasoning_steps)
    assert res.payload is not None
    assert res.payload.win_probability == 0.94
    fallback.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_tier1_failure_falls_back_to_tier2_llama_70b():
    """Rate limit / API failure on Tier 1 seamlessly falls back to Tier 2 Llama 3.3 70B."""
    primary = MagicMock()
    primary.ainvoke = AsyncMock(side_effect=TimeoutError("429 Rate Limit Exceeded"))

    fallback_json = json.dumps(
        {
            "win_probability": 0.91,
            "executive_summary": "Llama 3.3 70B fallback confirmed §11 compliance.",
            "rebuttal_statement": "Formal rebuttal prepared by Tier 2 fallback.",
            "customer_message": None,
            "evidence_citations": ["Signature card verified."],
            "reasoning_steps": ["Evaluated proof of delivery on Tier 2."],
        }
    )
    fallback = MagicMock()
    fallback.ainvoke = AsyncMock(return_value=_make_ai_msg(fallback_json))

    settings = Settings(OPENROUTER_API_KEY="sk-or-live-test-key", ENVIRONMENT="test")
    orchestrator = MultiModelLLMOrchestrator(
        settings=settings, primary_llm=primary, fallback_llm=fallback
    )

    res = await orchestrator.invoke_with_fallback("system", "user")

    assert res.tier_used == OrchestrationTier.TIER_2_LLAMA_70B
    assert res.model_name == settings.OPENROUTER_FALLBACK_MODEL
    assert res.payload is not None
    assert res.payload.win_probability == 0.91
    assert len(res.fallback_reasons) == 1
    assert "Tier 1" in res.fallback_reasons[0]


@pytest.mark.asyncio
async def test_tier1_and_tier2_failure_falls_back_to_tier3_heuristics():
    """Total OpenRouter failure degrades cleanly to Tier 3 deterministic heuristics."""
    primary = MagicMock()
    primary.ainvoke = AsyncMock(side_effect=RuntimeError("OpenRouter 503"))
    fallback = MagicMock()
    fallback.ainvoke = AsyncMock(side_effect=RuntimeError("Network Unreachable"))

    settings = Settings(OPENROUTER_API_KEY="sk-or-live-test-key", ENVIRONMENT="test")
    orchestrator = MultiModelLLMOrchestrator(
        settings=settings, primary_llm=primary, fallback_llm=fallback
    )

    res = await orchestrator.invoke_with_fallback("system", "user")

    assert res.tier_used == OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC
    assert res.payload is None
    assert len(res.fallback_reasons) == 3


@pytest.mark.asyncio
async def test_mock_api_key_routes_directly_to_tier3():
    """Mock / missing API key routes deterministically to Tier 3 without network calls."""
    settings = Settings(OPENROUTER_API_KEY="mock_openrouter_api_key", ENVIRONMENT="test")
    orchestrator = MultiModelLLMOrchestrator(settings=settings)

    res = await orchestrator.invoke_with_fallback("system", "user")

    assert res.tier_used == OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC
    assert res.payload is None


@pytest.mark.asyncio
async def test_specialist_respects_compliance_cap_even_when_llm_optimistic():
    """Compliance guardrails ($750 signature mandate) strictly cap Tier 1 LLM P(win)."""
    optimistic_json = json.dumps(
        {
            "win_probability": 0.98,
            "executive_summary": "Optimistic LLM summary",
            "rebuttal_statement": "Rebuttal text",
            "customer_message": None,
            "evidence_citations": [],
            "reasoning_steps": ["LLM attempted high score."],
        }
    )
    primary = MagicMock()
    primary.ainvoke = AsyncMock(
        return_value=_make_ai_msg(f"<thought>Analyzing</thought>\n{optimistic_json}")
    )
    settings = Settings(OPENROUTER_API_KEY="sk-or-live-test-key", ENVIRONMENT="test")
    orchestrator = MultiModelLLMOrchestrator(settings=settings, primary_llm=primary)
    agent = INRAgent(orchestrator=orchestrator)

    dispute = PayPalDisputeResource(
        dispute_id="PP-D-CAP-TEST",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="900.00"),
    )
    carrier = CarrierTrackingInfo(
        tracking_number="TRK-NOSIG",
        carrier_name="FedEx",
        status="DELIVERED",
        ship_date="2026-10-10T10:00:00Z",
        delivered_date="2026-10-14T10:00:00Z",
        destination_address="100 Main St, Austin, TX",
        signed_by=None,  # Missing required >= $750 signature
    )
    warehouse = WarehouseFulfillmentInfo(
        order_id="ORD-CAP",
        pack_timestamp="2026-10-10T08:00:00Z",
        warehouse_id="WH-1",
        packer_id="P-1",
        scale_measured_weight_kg=1.0,
        expected_weight_kg=1.0,
        weight_delta_percent=0.0,
        tamper_seal_id="SEAL-1",
        packing_station_photo_url="https://example.com/qa.jpg",
    )
    order = OrderCustomerInfo(
        order_id="ORD-CAP",
        transaction_id="TXN-CAP",
        customer_id="C-CAP",
        customer_name="Alex Doe",
        customer_email="alex@example.com",
        order_date="2026-10-09T10:00:00Z",
        total_amount=900.0,
        shipping_address="100 Main St, Austin, TX",
    )
    compliance = SellerProtectionComplianceEngine().audit_dispute(dispute, carrier, order)

    evaluation = await agent.analyze(
        SpecialistContext(
            dispute=dispute,
            carrier=carrier,
            warehouse=warehouse,
            order=order,
            compliance=compliance,
            dispute_fee=15.0,
        )
    )

    assert evaluation.llm_tier_used == OrchestrationTier.TIER_1_GEMINI_THINKING
    assert evaluation.seller_rights_met is False
    assert evaluation.win_probability == 0.05


@pytest.mark.asyncio
async def test_empty_response_is_retried_on_the_same_tier():
    """Free providers sometimes return empty content; one retry keeps the request on Tier 1."""
    good = _make_ai_msg(
        json.dumps({"customer_message": "Your parcel was delivered.", "reasoning_steps": []})
    )
    primary = MagicMock()
    primary.ainvoke = AsyncMock(side_effect=[_make_ai_msg(""), good])
    fallback = MagicMock()
    fallback.ainvoke = AsyncMock()

    settings = Settings(OPENROUTER_API_KEY="sk-or-live-test-key", ENVIRONMENT="test")
    orchestrator = MultiModelLLMOrchestrator(
        settings=settings, primary_llm=primary, fallback_llm=fallback
    )

    res = await orchestrator.invoke_with_fallback("system", "user")

    assert res.tier_used == OrchestrationTier.TIER_1_GEMINI_THINKING
    assert res.payload is not None and res.payload.customer_message == "Your parcel was delivered."
    assert primary.ainvoke.await_count == 2
    fallback.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeated_empty_responses_fall_back_to_tier2():
    """If the primary stays empty after its retry, the fallback model answers."""
    primary = MagicMock()
    primary.ainvoke = AsyncMock(return_value=_make_ai_msg(""))
    fallback = MagicMock()
    fallback.ainvoke = AsyncMock(
        return_value=_make_ai_msg(
            json.dumps({"customer_message": "Fallback reply.", "reasoning_steps": []})
        )
    )

    settings = Settings(OPENROUTER_API_KEY="sk-or-live-test-key", ENVIRONMENT="test")
    orchestrator = MultiModelLLMOrchestrator(
        settings=settings, primary_llm=primary, fallback_llm=fallback
    )

    res = await orchestrator.invoke_with_fallback("system", "user")

    assert res.tier_used == OrchestrationTier.TIER_2_LLAMA_70B
    assert res.payload is not None and res.payload.customer_message == "Fallback reply."
    assert primary.ainvoke.await_count == settings.LLM_EMPTY_RESPONSE_ATTEMPTS


def test_routes_use_nvidia_first_with_openrouter_backup():
    """With both keys, NIM serves Tier 1/2 and OpenRouter is the cross-provider backup."""
    settings = Settings(
        NVIDIA_API_KEY="nvapi-live-test-key",
        OPENROUTER_API_KEY="sk-or-live-test-key",
        ENVIRONMENT="test",
    )
    routes = MultiModelLLMOrchestrator(settings=settings).model_routes()

    assert [(r.tier, r.provider) for r in routes] == [
        (OrchestrationTier.TIER_1_GEMINI_THINKING, "nvidia"),
        (OrchestrationTier.TIER_2_LLAMA_70B, "nvidia"),
        (OrchestrationTier.OPENROUTER_BACKUP, "openrouter"),
    ]
    assert routes[0].model_name == settings.NVIDIA_PRIMARY_MODEL
    assert routes[2].model_name == settings.OPENROUTER_BACKUP_MODEL


def test_routes_without_keys_for_a_provider():
    """NIM alone has no backup; OpenRouter alone serves both tiers as before."""
    nim_only = Settings(NVIDIA_API_KEY="nvapi-live-test-key", ENVIRONMENT="test")
    assert [r.provider for r in MultiModelLLMOrchestrator(settings=nim_only).model_routes()] == [
        "nvidia",
        "nvidia",
    ]

    openrouter_only = Settings(OPENROUTER_API_KEY="sk-or-live-test-key", ENVIRONMENT="test")
    routes = MultiModelLLMOrchestrator(settings=openrouter_only).model_routes()
    assert [r.provider for r in routes] == ["openrouter", "openrouter"]
    assert routes[0].model_name == openrouter_only.OPENROUTER_PRIMARY_MODEL


@pytest.mark.asyncio
async def test_openrouter_backup_answers_when_both_nvidia_models_fail():
    """A NIM outage or rate limit on both models is covered by the OpenRouter backup."""
    primary = MagicMock()
    primary.ainvoke = AsyncMock(side_effect=RuntimeError("NIM 429 Too Many Requests"))
    fallback = MagicMock()
    fallback.ainvoke = AsyncMock(side_effect=RuntimeError("NIM 503"))
    backup = MagicMock()
    backup.ainvoke = AsyncMock(
        return_value=_make_ai_msg(
            json.dumps({"customer_message": "Backup reply.", "reasoning_steps": []})
        )
    )

    settings = Settings(
        NVIDIA_API_KEY="nvapi-live-test-key",
        OPENROUTER_API_KEY="sk-or-live-test-key",
        ENVIRONMENT="test",
    )
    orchestrator = MultiModelLLMOrchestrator(
        settings=settings, primary_llm=primary, fallback_llm=fallback
    )
    orchestrator._clients[("openrouter", settings.OPENROUTER_BACKUP_MODEL)] = backup

    res = await orchestrator.invoke_with_fallback("system", "user")

    assert res.tier_used == OrchestrationTier.OPENROUTER_BACKUP
    assert res.model_name == settings.OPENROUTER_BACKUP_MODEL
    assert res.payload is not None and res.payload.customer_message == "Backup reply."
    assert [r.split(" (")[0] for r in res.fallback_reasons] == ["Tier 1", "Tier 2"]


def test_chat_purpose_uses_fast_chat_models():
    """Buyer conversation uses the speed-first NIM chain; analysis keeps the quality-first chain."""
    settings = Settings(
        NVIDIA_API_KEY="nvapi-live-test-key",
        OPENROUTER_API_KEY="sk-or-live-test-key",
        ENVIRONMENT="test",
    )
    chat = MultiModelLLMOrchestrator(settings=settings, purpose="chat").model_routes()
    analysis = MultiModelLLMOrchestrator(settings=settings).model_routes()

    assert [r.model_name for r in chat] == [
        settings.NVIDIA_CHAT_PRIMARY_MODEL,
        settings.NVIDIA_CHAT_FALLBACK_MODEL,
        settings.OPENROUTER_BACKUP_MODEL,
    ]
    assert [r.model_name for r in analysis][:2] == [
        settings.NVIDIA_PRIMARY_MODEL,
        settings.NVIDIA_FALLBACK_MODEL,
    ]
