"""
End-to-end integration tests for the Automated PayPal Dispute Resolution Engine.
Validates all three decision paths (De-escalation, Defense, Concession), HITL queue & override,
idempotency, and PDF generation.
"""

import json
import os
import pytest
from httpx import AsyncClient

from src.models.schemas import PipelineExecutionStatus
from src.workflows.dispute_pipeline import get_dispute_pipeline


@pytest.mark.asyncio
async def test_e2e_de_escalation_path(
    async_client: AsyncClient,
    sample_inquiry_payload: dict,
    sign_webhook_payload,
):
    """
    E2E Test Path 1: INQUIRY Stage -> De-escalate via message/offer.
    """
    raw_body = json.dumps(sample_inquiry_payload).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    resp = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "PROCESSED"
    assert data["dispute_id"] == "PP-D-INQUIRY-9001"
    assert data["pipeline_status"] == PipelineExecutionStatus.DE_ESCALATED.value
    assert "DE_ESCALATION" in data["action_taken"] or "OFFER" in data["action_taken"]

    # Verify dispute can be retrieved via GET endpoint
    get_resp = await async_client.get(f"/api/v1/disputes/{data['dispute_id']}")
    assert get_resp.status_code == 200
    record = get_resp.json()
    assert record["pipeline_status"] == PipelineExecutionStatus.DE_ESCALATED.value
    assert record["stage"] == "INQUIRY"


@pytest.mark.asyncio
async def test_e2e_defense_path(
    async_client: AsyncClient,
    sample_claim_high_pwin_payload: dict,
    sign_webhook_payload,
):
    """
    E2E Test Path 2: CLAIM Stage & P(win) >= 0.70 -> Defend via provide-evidence with PDF dossier.
    """
    raw_body = json.dumps(sample_claim_high_pwin_payload).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    resp = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "PROCESSED"
    assert data["dispute_id"] == "PP-D-DEFEND-7701"
    assert data["pipeline_status"] == PipelineExecutionStatus.DEFENDED.value
    assert data["action_taken"] == "PROVIDED_EVIDENCE_DOSSIER"
    assert data["win_probability"] >= 0.70

    # Verify generated PDF dossier can be downloaded
    pdf_resp = await async_client.get(f"/api/v1/disputes/{data['dispute_id']}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    # PDF magic bytes "%PDF"
    assert pdf_resp.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_e2e_concession_path(
    async_client: AsyncClient,
    sample_claim_low_pwin_payload: dict,
    sign_webhook_payload,
):
    """
    E2E Test Path 3: CLAIM Stage & P(win) < 0.70 -> Concede via accept-claim.
    """
    raw_body = json.dumps(sample_claim_low_pwin_payload).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    resp = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "PROCESSED"
    assert data["dispute_id"] == "PP-D-CONCEDE-3301"
    assert data["pipeline_status"] == PipelineExecutionStatus.CONCEDED.value
    assert data["action_taken"] == "ACCEPTED_CLAIM_CONCESSION"
    assert data["win_probability"] < 0.70


@pytest.mark.asyncio
async def test_e2e_hitl_queue_and_override_flow(
    async_client: AsyncClient,
    sample_claim_hitl_high_value_payload: dict,
    sign_webhook_payload,
):
    """
    E2E Test Path 4: High Value Order ($750 > $300) -> Flagged for HITL review.
    Human operator reviews and applies manual override.
    """
    dispute_id = sample_claim_hitl_high_value_payload["resource"]["dispute_id"]
    raw_body = json.dumps(sample_claim_hitl_high_value_payload).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    # 1. Ingest Webhook
    resp = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_status"] == PipelineExecutionStatus.FLAGGED_HITL.value
    assert data["hitl_flagged"] is True

    # 2. Check HITL Queue
    queue_resp = await async_client.get("/api/v1/disputes/hitl/queue")
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    assert any(item["dispute_id"] == dispute_id for item in queue)

    # 3. Human reviewer overrides to DEFEND
    override_payload = {
        "reviewer_id": "OPERATOR_JANE_DOE",
        "action": "DEFEND",
        "override_reason": "High-value VIP order with confirmed delivery telemetry.",
    }
    override_resp = await async_client.post(
        f"/api/v1/disputes/{dispute_id}/hitl/override",
        json=override_payload,
    )
    assert override_resp.status_code == 200
    updated_record = override_resp.json()
    assert updated_record["pipeline_status"] == PipelineExecutionStatus.DEFENDED.value
    assert updated_record["hitl_reviewed_by"] == "OPERATOR_JANE_DOE"
    assert updated_record["action_taken"] == "HUMAN_OVERRIDE_DEFENDED"

    # 4. Confirm dispute is cleared from HITL queue
    queue_resp2 = await async_client.get("/api/v1/disputes/hitl/queue")
    queue2 = queue_resp2.json()
    assert not any(item["dispute_id"] == dispute_id for item in queue2)


@pytest.mark.asyncio
async def test_e2e_idempotent_processing(
    async_client: AsyncClient,
    sample_claim_high_pwin_payload: dict,
    sign_webhook_payload,
):
    """
    E2E Test Path 5: Verifies that re-submitting an already processed dispute is idempotent.
    """
    raw_body = json.dumps(sample_claim_high_pwin_payload).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    # First call
    resp1 = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp1.status_code == 200

    # Second identical call
    resp2 = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp2.status_code == 200

    # Verify record in registry is not duplicated
    list_resp = await async_client.get("/api/v1/disputes")
    disputes = [d for d in list_resp.json() if d["dispute_id"] == "PP-D-DEFEND-7701"]
    assert len(disputes) == 1


@pytest.mark.asyncio
async def test_e2e_dispute_stats_summary(async_client: AsyncClient):
    """
    E2E Test Path 6: Verify aggregate metrics and stats summary endpoint.
    """
    stats_resp = await async_client.get("/api/v1/disputes/stats/summary")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "total_disputes" in stats
    assert "defended_count" in stats
    assert "conceded_count" in stats
    assert "estimated_dispute_fees_avoided" in stats
    assert stats["total_disputes"] >= 3


@pytest.mark.asyncio
async def test_e2e_dispute_resolved_webhook(
    async_client: AsyncClient,
    sample_claim_high_pwin_payload: dict,
    sign_webhook_payload,
):
    """
    Test CUSTOMER.DISPUTE.RESOLVED event transitions dispute to RESOLVED.
    """
    resolved_event = dict(sample_claim_high_pwin_payload)
    resolved_event["id"] = "WH-EVT-RESOLVED-009"
    resolved_event["event_type"] = "CUSTOMER.DISPUTE.RESOLVED"

    raw_body = json.dumps(resolved_event).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    resp = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_status"] == PipelineExecutionStatus.RESOLVED.value


@pytest.mark.asyncio
async def test_e2e_webhook_signature_failure_returns_400(async_client: AsyncClient):
    """
    Test invalid signature triggers 400 Bad Request.
    """
    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-TRANSMISSION-ID": "T-1",
        "PAYPAL-CERT-URL": "https://api.paypal.com/cert.pem",
        "PAYPAL-TRANSMISSION-SIG": "invalid_base64_sig==",
        "PAYPAL-TRANSMISSION-TIME": "2026-10-18T12:00:00Z",
    }
    resp = await async_client.post("/api/v1/paypal/webhook", content=b"{}", headers=headers)
    assert resp.status_code == 400
    assert "Webhook verification failure" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_e2e_dispute_not_found(async_client: AsyncClient):
    """Test 404 returned for nonexistent dispute."""
    resp = await async_client.get("/api/v1/disputes/NONEXISTENT_DISPUTE_ID")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_e2e_pdf_not_found_for_inquiry(async_client: AsyncClient):
    """Test 404 returned when downloading PDF for dispute that was de-escalated (no dossier generated)."""
    resp = await async_client.get("/api/v1/disputes/PP-D-INQUIRY-9001/pdf")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_e2e_hitl_override_additional_actions(
    async_client: AsyncClient,
    sample_claim_hitl_high_value_payload: dict,
    sign_webhook_payload,
):
    """
    Test HITL override with CONCEDE, SEND_MESSAGE, and MAKE_OFFER actions.
    """
    payload_copy = json.loads(json.dumps(sample_claim_hitl_high_value_payload))
    payload_copy["resource"]["dispute_id"] = "PP-D-HITL-MULTI-99"
    payload_copy["resource"]["disputed_transactions"][0]["seller_transaction_id"] = "TXN-MULTI-99"

    raw_body = json.dumps(payload_copy).encode("utf-8")
    headers = sign_webhook_payload(raw_body)
    await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)

    # 1. Override with CONCEDE
    concede_resp = await async_client.post(
        "/api/v1/disputes/PP-D-HITL-MULTI-99/hitl/override",
        json={"reviewer_id": "REVIEWER_A", "action": "CONCEDE", "override_reason": "Conceding upon buyer request"},
    )
    assert concede_resp.status_code == 200
    assert concede_resp.json()["pipeline_status"] == PipelineExecutionStatus.CONCEDED.value

    # 2. Override with SEND_MESSAGE
    msg_resp = await async_client.post(
        "/api/v1/disputes/PP-D-HITL-MULTI-99/hitl/override",
        json={"reviewer_id": "REVIEWER_B", "action": "SEND_MESSAGE", "override_reason": "Sending inquiry follow-up"},
    )
    assert msg_resp.status_code == 200
    assert msg_resp.json()["pipeline_status"] == PipelineExecutionStatus.DE_ESCALATED.value

    # 3. Override with MAKE_OFFER
    offer_resp = await async_client.post(
        "/api/v1/disputes/PP-D-HITL-MULTI-99/hitl/override",
        json={"reviewer_id": "REVIEWER_C", "action": "MAKE_OFFER", "override_reason": "Offering courtesy discount", "adjusted_offer_amount": 100.0},
    )
    assert offer_resp.status_code == 200
    assert offer_resp.json()["pipeline_status"] == PipelineExecutionStatus.DE_ESCALATED.value


@pytest.mark.asyncio
async def test_e2e_dispute_filters_and_health_check(async_client: AsyncClient):
    """Test filtering disputes by stage & status and health check."""
    # Filter by stage
    resp = await async_client.get("/api/v1/disputes?stage=INQUIRY")
    assert resp.status_code == 200
    records = resp.json()
    assert all(r["stage"] == "INQUIRY" for r in records)

    # Health check
    health_resp = await async_client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # Root
    root_resp = await async_client.get("/")
    assert root_resp.status_code == 200

