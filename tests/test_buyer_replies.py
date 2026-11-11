"""
Buyer reply handling: CUSTOMER.DISPUTE.UPDATED webhooks carrying new buyer messages must be stored,
deduplicated, and answered (AI first, safe template when the models are unavailable).
"""

import copy
import json
import uuid

import pytest
from httpx import AsyncClient

from src.models.schemas import PipelineExecutionStatus
from src.services.llm_orchestrator import (
    LLMArbitrationPayload,
    LLMOrchestrationResult,
    OrchestrationTier,
)
from src.workflows.dispute_pipeline import get_dispute_pipeline


def _with_new_ids(payload: dict) -> dict:
    """Copies a sample payload with fresh event and dispute IDs so tests don't share state."""
    fresh = copy.deepcopy(payload)
    suffix = uuid.uuid4().hex[:8].upper()
    fresh["id"] = f"WH-EVT-{suffix}"
    fresh["resource"]["dispute_id"] = f"PP-D-REPLY-{suffix}"
    return fresh


def _update_event(created: dict, messages: list[dict]) -> dict:
    """Builds the CUSTOMER.DISPUTE.UPDATED event PayPal sends when the thread changes."""
    event = copy.deepcopy(created)
    event["id"] = f"WH-EVT-UPD-{uuid.uuid4().hex[:8].upper()}"
    event["event_type"] = "CUSTOMER.DISPUTE.UPDATED"
    event["resource"]["messages"] = messages
    return event


async def _post(async_client: AsyncClient, sign_webhook_payload, event: dict):
    raw = json.dumps(event).encode("utf-8")
    return await async_client.post(
        "/api/v1/paypal/webhook", content=raw, headers=sign_webhook_payload(raw)
    )


BUYER_MSG = {
    "posted_by": "BUYER",
    "time_posted": "2026-10-19T10:00:00Z",
    "content": "Where is my package?",
}


@pytest.mark.asyncio
async def test_buyer_reply_is_stored_and_answered(
    async_client: AsyncClient, sample_claim_high_pwin_payload: dict, sign_webhook_payload
):
    created = _with_new_ids(sample_claim_high_pwin_payload)
    assert (await _post(async_client, sign_webhook_payload, created)).status_code == 200
    dispute_id = created["resource"]["dispute_id"]

    resp = await _post(async_client, sign_webhook_payload, _update_event(created, [BUYER_MSG]))
    assert resp.status_code == 200
    assert resp.json()["pipeline_status"] == PipelineExecutionStatus.DEFENDED.value

    record = (await async_client.get(f"/api/v1/disputes/{dispute_id}")).json()
    senders = [m["sender"] for m in record["messages"]]
    assert senders == ["BUYER", "SELLER"]
    assert record["messages"][0]["content"] == "Where is my package?"
    # Tests run without an OpenRouter key, so the safe template answers.
    reply = record["messages"][1]
    assert reply["source"] == "TEMPLATE_REPLY"
    assert reply["llm_tier_used"] == OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC.value
    assert any("Replied to the buyer" in entry for entry in record["audit_trail"])


@pytest.mark.asyncio
async def test_repeated_webhook_does_not_duplicate_or_reply_twice(
    async_client: AsyncClient, sample_claim_high_pwin_payload: dict, sign_webhook_payload
):
    created = _with_new_ids(sample_claim_high_pwin_payload)
    await _post(async_client, sign_webhook_payload, created)
    dispute_id = created["resource"]["dispute_id"]

    update = _update_event(created, [BUYER_MSG])
    await _post(async_client, sign_webhook_payload, update)
    await _post(async_client, sign_webhook_payload, update)  # PayPal retry of the same event

    record = (await async_client.get(f"/api/v1/disputes/{dispute_id}")).json()
    assert [m["sender"] for m in record["messages"]] == ["BUYER", "SELLER"]


@pytest.mark.asyncio
async def test_echoed_seller_reply_is_not_duplicated_and_new_buyer_message_is_answered(
    async_client: AsyncClient, sample_claim_high_pwin_payload: dict, sign_webhook_payload
):
    created = _with_new_ids(sample_claim_high_pwin_payload)
    await _post(async_client, sign_webhook_payload, created)
    dispute_id = created["resource"]["dispute_id"]

    await _post(async_client, sign_webhook_payload, _update_event(created, [BUYER_MSG]))
    our_reply = (await async_client.get(f"/api/v1/disputes/{dispute_id}")).json()["messages"][1]

    # PayPal echoes our reply back with its own timestamp, alongside the buyer's next message.
    thread = [
        BUYER_MSG,
        {
            "posted_by": "SELLER",
            "time_posted": "2026-10-19T10:05:00Z",
            "content": our_reply["content"],
        },
        {
            "posted_by": "BUYER",
            "time_posted": "2026-10-19T11:00:00Z",
            "content": "Found it, thanks!",
        },
    ]
    await _post(async_client, sign_webhook_payload, _update_event(created, thread))

    record = (await async_client.get(f"/api/v1/disputes/{dispute_id}")).json()
    assert [m["sender"] for m in record["messages"]] == ["BUYER", "SELLER", "BUYER", "SELLER"]


@pytest.mark.asyncio
async def test_flagged_dispute_stores_message_without_auto_reply(
    async_client: AsyncClient, sample_claim_hitl_high_value_payload: dict, sign_webhook_payload
):
    created = _with_new_ids(sample_claim_hitl_high_value_payload)
    resp = await _post(async_client, sign_webhook_payload, created)
    assert resp.json()["pipeline_status"] == PipelineExecutionStatus.FLAGGED_HITL.value
    dispute_id = created["resource"]["dispute_id"]

    await _post(async_client, sign_webhook_payload, _update_event(created, [BUYER_MSG]))

    record = (await async_client.get(f"/api/v1/disputes/{dispute_id}")).json()
    assert [m["sender"] for m in record["messages"]] == ["BUYER"]
    assert any("awaiting human review" in entry for entry in record["audit_trail"])


@pytest.mark.asyncio
async def test_ai_reply_is_used_when_the_model_answers(
    async_client: AsyncClient,
    sample_claim_high_pwin_payload: dict,
    sign_webhook_payload,
    monkeypatch,
):
    created = _with_new_ids(sample_claim_high_pwin_payload)
    await _post(async_client, sign_webhook_payload, created)
    dispute_id = created["resource"]["dispute_id"]

    async def fake_invoke(system_prompt: str, user_prompt: str) -> LLMOrchestrationResult:
        assert "Where is my package?" in user_prompt
        return LLMOrchestrationResult(
            tier_used=OrchestrationTier.TIER_1_GEMINI_THINKING,
            model_name="test-model",
            payload=LLMArbitrationPayload(customer_message="Your parcel was delivered on Oct 18."),
        )

    monkeypatch.setattr(
        get_dispute_pipeline().llm_orchestrator, "invoke_with_fallback", fake_invoke
    )
    await _post(async_client, sign_webhook_payload, _update_event(created, [BUYER_MSG]))

    reply = (await async_client.get(f"/api/v1/disputes/{dispute_id}")).json()["messages"][1]
    assert reply["content"] == "Your parcel was delivered on Oct 18."
    assert reply["source"] == "AI_REPLY"
    assert reply["llm_tier_used"] == OrchestrationTier.TIER_1_GEMINI_THINKING.value


@pytest.mark.asyncio
async def test_dashboard_message_and_simulated_buyer_reply_endpoints(
    async_client: AsyncClient, sample_claim_high_pwin_payload: dict, sign_webhook_payload
):
    created = _with_new_ids(sample_claim_high_pwin_payload)
    await _post(async_client, sign_webhook_payload, created)
    dispute_id = created["resource"]["dispute_id"]

    sent = await async_client.post(
        f"/api/v1/disputes/{dispute_id}/messages", json={"message": "Hi, checking in."}
    )
    assert sent.status_code == 200
    assert sent.json()["messages"][-1]["source"] == "DASHBOARD"

    simulated = await async_client.post(
        f"/api/v1/disputes/{dispute_id}/simulate-buyer-message",
        json={"message": "Still nothing here."},
    )
    assert simulated.status_code == 200
    senders = [m["sender"] for m in simulated.json()["messages"]]
    assert senders == ["SELLER", "BUYER", "SELLER"]

    missing = await async_client.post(
        "/api/v1/disputes/PP-D-NOPE/messages", json={"message": "hello"}
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_simulated_conversation_first_buyer_message_is_reason_template_then_ai(
    async_client: AsyncClient,
    sample_claim_high_pwin_payload: dict,
    sign_webhook_payload,
    monkeypatch,
):
    """First simulated buyer message uses the issue template; later ones are AI-written replies."""
    created = _with_new_ids(sample_claim_high_pwin_payload)  # item not received
    await _post(async_client, sign_webhook_payload, created)
    dispute_id = created["resource"]["dispute_id"]
    url = f"/api/v1/disputes/{dispute_id}/simulate-buyer-message"

    first = (await async_client.post(url)).json()["messages"]
    assert first[0]["sender"] == "BUYER"
    assert first[0]["source"] == "SIMULATED_TEMPLATE"
    assert "never arrived" in first[0]["content"]
    assert first[1]["sender"] == "SELLER"  # merchant reply follows automatically

    seen_prompts: list[str] = []

    async def fake_invoke(system_prompt: str, user_prompt: str) -> LLMOrchestrationResult:
        seen_prompts.append(system_prompt + user_prompt)
        return LLMOrchestrationResult(
            tier_used=OrchestrationTier.TIER_1_GEMINI_THINKING,
            model_name="test-model",
            payload=LLMArbitrationPayload(
                customer_message="I found it behind the planter, thanks!"
            ),
        )

    monkeypatch.setattr(
        get_dispute_pipeline().llm_orchestrator, "invoke_with_fallback", fake_invoke
    )
    second = (await async_client.post(url)).json()["messages"]

    buyer_reply = second[2]
    assert buyer_reply["sender"] == "BUYER"
    assert buyer_reply["source"] == "SIMULATED_AI"
    assert buyer_reply["content"] == "I found it behind the planter, thanks!"
    # The AI buyer read the merchant's reply before answering.
    assert first[1]["content"] in seen_prompts[0]
    assert second[3]["sender"] == "SELLER"


@pytest.mark.asyncio
async def test_first_buyer_message_template_matches_issue_type(
    async_client: AsyncClient, sample_claim_high_pwin_payload: dict, sign_webhook_payload
):
    payload = _with_new_ids(sample_claim_high_pwin_payload)
    payload["resource"]["dispute_reason"] = "CANCELED_RECURRING_BILLING"
    await _post(async_client, sign_webhook_payload, payload)
    dispute_id = payload["resource"]["dispute_id"]

    msgs = (
        await async_client.post(f"/api/v1/disputes/{dispute_id}/simulate-buyer-message")
    ).json()["messages"]
    assert "subscription" in msgs[0]["content"]


@pytest.mark.asyncio
async def test_inquiry_opening_message_is_stored_in_thread(
    async_client: AsyncClient, sample_inquiry_payload: dict, sign_webhook_payload
):
    """The merchant's opening de-escalation message is saved, so the thread starts with it."""
    created = _with_new_ids(sample_inquiry_payload)
    await _post(async_client, sign_webhook_payload, created)
    record = (
        await async_client.get(f"/api/v1/disputes/{created['resource']['dispute_id']}")
    ).json()

    assert record["pipeline_status"] == PipelineExecutionStatus.DE_ESCALATED.value
    assert len(record["messages"]) == 1
    assert record["messages"][0]["sender"] == "SELLER"
