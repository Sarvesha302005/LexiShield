"""
Integration & Unit Tests for Cryptographic SHA-256 PDF Dossier Generation,
Exhibit C SaaS Telemetry, Transparent Thought Traces, and Pipeline Audit Persistence.
"""

import hashlib
import json

import pytest
from httpx import AsyncClient

from src.models.arbitration import ArbitrationAction, ArbitrationDecision
from src.models.schemas import (
    BillingTelemetryInfo,
    CarrierTrackingInfo,
    DisputeReason,
    DisputeStage,
    Money,
    OrderCustomerInfo,
    PayPalDisputeResource,
    PipelineExecutionStatus,
    WarehouseFulfillmentInfo,
)
from src.services.pdf_generator import PDFGenerator


def test_pdf_generator_sha256_and_exhibit_c_billing_and_thought_trace(tmp_path):
    """
    Verify ReportLab PDF generator computes deterministic SHA-256 digest,
    renders Exhibit C SaaS session telemetry, and escapes XML in <thought> traces.
    """
    gen = PDFGenerator(output_dir=str(tmp_path))
    dispute = PayPalDisputeResource(
        dispute_id="PP-PDF-SHA-01",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.CANCELED_RECURRING_BILLING,
        dispute_amount=Money(currency_code="USD", value="79.00"),
    )
    decision = ArbitrationDecision(
        dispute_id="PP-PDF-SHA-01",
        win_probability=0.92,
        expected_value=71.48,
        recommended_action=ArbitrationAction.PROVIDE_EVIDENCE,
        executive_summary="SaaS subscription assent & post-cancel logins verified.",
        rebuttal_statement="Clickwrap ToS & active API requests <100ms after cancel > threshold.",
        specialist_agent="BillingAgent",
        persona_mode="ADVERSARIAL_LEGAL_DEFENSE",
        llm_tier_used="TIER_1_GEMINI_THINKING",
        thought_trace="Verified <assent> & post-cancellation logins > 0.",
        reasoning_steps=["[Thought] Verified clickwrap assent & API calls."],
        seller_rights_met=True,
    )
    carrier = CarrierTrackingInfo(
        tracking_number="DIGITAL-LIC-01",
        carrier_name="Digital Fulfillment",
        status="DELIVERED",
        ship_date="2026-10-01T09:00:00Z",
        delivered_date="2026-10-01T09:00:00Z",
        destination_address="Cloud Delivery / 500 Howard St, San Francisco, CA",
    )
    warehouse = WarehouseFulfillmentInfo(
        order_id="ORD-SAAS-01",
        pack_timestamp="2026-10-01T09:00:00Z",
        warehouse_id="CLOUD-US-1",
        packer_id="AUTO-LIC",
        scale_measured_weight_kg=0.0,
        expected_weight_kg=0.0,
        weight_delta_percent=0.0,
        scanned_serials=["LIC-PRO-001"],
        tamper_seal_id="DIGITAL-SHA",
        packing_station_photo_url="https://cdn.example.com/digital.png",
    )
    order = OrderCustomerInfo(
        order_id="ORD-SAAS-01",
        transaction_id="TXN-SAAS-01",
        customer_id="CUST-SAAS-01",
        customer_name="Sophia Chen",
        customer_email="sophia@enterprise.io",
        order_date="2026-10-01T09:00:00Z",
        total_amount=79.00,
        shipping_address="Cloud Delivery / 500 Howard St, San Francisco, CA",
    )
    billing = BillingTelemetryInfo(
        order_id="ORD-SAAS-01",
        subscription_id="SUB-ORD-SAAS-01",
        clickwrap_assent_verified=True,
        clickwrap_assent_timestamp="2026-10-01T09:00:00Z",
        clickwrap_ip_address="24.130.88.12",
        cancellation_within_grace_period=False,
        post_cancellation_login_timestamps=["2026-10-14T08:15:22Z"],
        post_cancellation_api_requests=142,
        active_sessions_count=3,
        last_active_ip="24.130.88.12",
    )

    pdf_bytes, sha256_hex = gen.generate_rebuttal_dossier_with_hash(
        dispute=dispute,
        decision=decision,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        billing_result=billing,
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert len(sha256_hex) == 64
    assert sha256_hex == hashlib.sha256(pdf_bytes).hexdigest()


@pytest.mark.asyncio
async def test_e2e_billing_dispute_records_sha256_and_headers(
    async_client: AsyncClient,
    sign_webhook_payload,
):
    """E2E CANCELED_RECURRING_BILLING routes to BillingAgent, compiles PDF + SHA-256, and exposes X-Dossier-SHA256."""
    payload = {
        "id": "WH-EVT-BILL-001",
        "event_version": "1.0",
        "create_time": "2026-10-20T10:00:00Z",
        "resource_type": "dispute",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "summary": "Canceled recurring subscription dispute.",
        "resource": {
            "dispute_id": "PP-D-BILL-SHA-901",
            "create_time": "2026-10-20T09:55:00Z",
            "dispute_stage": "CLAIM",
            "dispute_reason": "CANCELED_RECURRING_BILLING",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "dispute_amount": {"currency_code": "USD", "value": "79.00"},
            "disputed_transactions": [
                {
                    "seller_transaction_id": "TXN-BILL-901",
                    "invoice_number": "ORD-BILL-901",
                    "gross_amount": {"currency_code": "USD", "value": "79.00"},
                    "buyer": {"name": "Sophia Chen", "email": "sophia@enterprise.io"},
                }
            ],
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    resp = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pipeline_status"] == PipelineExecutionStatus.DEFENDED.value

    record_resp = await async_client.get("/api/v1/disputes/PP-D-BILL-SHA-901")
    assert record_resp.status_code == 200
    record = record_resp.json()
    assert record["specialist_agent"] == "BillingAgent"
    assert record["seller_rights_met"] is True
    assert record["pdf_dossier_sha256"] is not None
    assert len(record["pdf_dossier_sha256"]) == 64
    assert any(
        f"Evidentiary Dossier SHA-256: {record['pdf_dossier_sha256']}" in entry
        for entry in record["audit_trail"]
    )

    pdf_resp = await async_client.get("/api/v1/disputes/PP-D-BILL-SHA-901/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["X-Dossier-SHA256"] == record["pdf_dossier_sha256"]
    assert hashlib.sha256(pdf_resp.content).hexdigest() == record["pdf_dossier_sha256"]


@pytest.mark.asyncio
async def test_e2e_snad_generates_rma_and_simulate_normalizes_unauthorized(
    async_client: AsyncClient,
):
    """
    Verify /api/v1/disputes/simulate normalizes UNAUTHORIZED_TRANSACTION to FraudAgent
    and SNAD disputes automatically generate an authorized RMA tracking record.
    """
    sim_fraud = await async_client.post(
        "/api/v1/disputes/simulate",
        json={
            "order_id": "ORD-SIM-FRAUD-01",
            "customer_name": "Alex Mercer",
            "customer_email": "alex@example.com",
            "reason": "UNAUTHORIZED_TRANSACTION",
            "stage": "CLAIM",
            "amount": 175.00,
        },
    )
    assert sim_fraud.status_code == 200
    fraud_rec = sim_fraud.json()
    assert fraud_rec["reason"] == "UNAUTHORISED"
    assert fraud_rec["specialist_agent"] == "FraudAgent"
    assert fraud_rec["pipeline_status"] == PipelineExecutionStatus.DEFENDED.value
    assert fraud_rec["pdf_dossier_sha256"] is not None

    sim_snad = await async_client.post(
        "/api/v1/disputes/simulate",
        json={
            "order_id": "ORD-SIM-SNAD-01",
            "customer_name": "Elena Rostova",
            "customer_email": "elena@example.com",
            "reason": "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED",
            "stage": "CLAIM",
            "amount": 199.00,
        },
    )
    assert sim_snad.status_code == 200
    snad_rec = sim_snad.json()
    assert snad_rec["specialist_agent"] == "SNADAgent"
    assert snad_rec["rma_number"] is not None
    assert snad_rec["rma_number"].startswith("RMA-")


@pytest.mark.asyncio
async def test_e2e_hitl_high_value_compiles_dossier_upfront_with_sha256(
    async_client: AsyncClient,
    sample_claim_hitl_high_value_payload: dict,
    sign_webhook_payload,
):
    """Per Decision Matrix row 2: High-value (> $300) CLAIM compiles full PDF dossier + SHA-256 for HITL review."""
    payload = json.loads(json.dumps(sample_claim_hitl_high_value_payload))
    payload["resource"]["dispute_id"] = "PP-D-HITL-SHA-801"
    raw_body = json.dumps(payload).encode("utf-8")
    headers = sign_webhook_payload(raw_body)

    resp = await async_client.post("/api/v1/paypal/webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pipeline_status"] == PipelineExecutionStatus.FLAGGED_HITL.value

    rec_resp = await async_client.get("/api/v1/disputes/PP-D-HITL-SHA-801")
    assert rec_resp.status_code == 200
    rec = rec_resp.json()
    assert rec["pdf_dossier_path"] is not None
    assert rec["pdf_dossier_sha256"] is not None
    assert len(rec["pdf_dossier_sha256"]) == 64

    pdf_resp = await async_client.get("/api/v1/disputes/PP-D-HITL-SHA-801/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["X-Dossier-SHA256"] == rec["pdf_dossier_sha256"]


@pytest.mark.asyncio
async def test_sqlite_db_persistence_and_sync_roundtrip(tmp_path, monkeypatch):
    """Verify init_db() schema + _save_record_to_db + sync_from_db preserve SHA-256 and agent metadata."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from src.database.models import Base
    from src.workflows.dispute_pipeline import DisputePipeline

    monkeypatch.chdir(tmp_path)
    db_file = tmp_path / "lexishield.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await test_engine.dispose()

    p1 = DisputePipeline()
    dispute = PayPalDisputeResource(
        dispute_id="PP-DB-ROUND-01",
        create_time="2026-10-20T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.CANCELED_RECURRING_BILLING,
        dispute_amount=Money(currency_code="USD", value="79.00"),
    )
    saved = await p1.execute_dispute_resolution(
        dispute=dispute, correlation_id="CORR-DB-01", merchant_id="default-merchant"
    )
    assert saved.pdf_dossier_sha256 is not None

    p2 = DisputePipeline()
    await p2.sync_from_db()
    reloaded = p2.get_record("PP-DB-ROUND-01")
    assert reloaded is not None
    assert reloaded.specialist_agent == "BillingAgent"
    assert reloaded.pdf_dossier_sha256 == saved.pdf_dossier_sha256
    assert reloaded.seller_rights_met is True
    assert reloaded.telemetry_billing is not None
