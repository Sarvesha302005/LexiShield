"""
Unit tests for the Horizontal Specialist Agentic Hierarchy:
DisputeSupervisor, INRAgent, SNADAgent, FraudAgent, BillingAgent,
Stage-Aware Dynamic Personas, and 'Seller Rights First' Universal Defense Policy.
"""

import pytest

from src.agents import (
    BillingAgent,
    DisputeSupervisor,
    FraudAgent,
    INRAgent,
    PersonaMode,
    SNADAgent,
)
from src.models.arbitration import ArbitrationAction
from src.models.schemas import (
    BillingTelemetryInfo,
    CarrierTrackingInfo,
    DisputeReason,
    DisputeStage,
    Money,
    OrderCustomerInfo,
    PayPalDisputeResource,
    WarehouseFulfillmentInfo,
)
from src.services.compliance import SellerProtectionComplianceEngine
from src.services.visa_ce3 import VisaCompellingEvidenceEngine


def _make_base_telemetry(
    amount: float = 150.0,
    carrier_status: str = "DELIVERED",
    signed_by: str | None = "J. DOE",
    weight_delta: float = 0.0,
    qa_passed: bool = True,
    past_orders: int = 6,
    merchant_dispute_ratio: float = 0.004,
) -> tuple[CarrierTrackingInfo, WarehouseFulfillmentInfo, OrderCustomerInfo]:
    carrier = CarrierTrackingInfo(
        tracking_number="TRK-AGENT-001",
        carrier_name="UPS Next Day Air",
        status=carrier_status,
        ship_date="2026-10-10T10:00:00Z",
        delivered_date="2026-10-13T14:20:00Z" if carrier_status == "DELIVERED" else None,
        destination_address="742 Evergreen Terrace, Springfield, OR 97477",
        gps_latitude=44.0531 if carrier_status == "DELIVERED" else None,
        gps_longitude=-123.0182 if carrier_status == "DELIVERED" else None,
        signed_by=signed_by,
    )
    warehouse = WarehouseFulfillmentInfo(
        order_id="ORD-AGENT-001",
        pack_timestamp="2026-10-09T09:00:00Z",
        warehouse_id="WH-WEST-01",
        packer_id="PACKER-42",
        scale_measured_weight_kg=1.50,
        expected_weight_kg=1.50,
        weight_delta_percent=weight_delta,
        scanned_barcodes=["UPC-1001"],
        scanned_serials=["SN-LEXI-88991"],
        tamper_seal_id="SEAL-88991",
        packing_station_photo_url="https://cdn.example.com/qa/88991.jpg",
        quality_inspection_passed=qa_passed,
    )
    order = OrderCustomerInfo(
        order_id="ORD-AGENT-001",
        transaction_id="TXN-AGENT-001",
        customer_id="CUST-AGENT-001",
        customer_name="Jane Mercer",
        customer_email="jane@example.com",
        order_date="2026-10-08T12:00:00Z",
        total_amount=amount,
        shipping_address="742 Evergreen Terrace, Springfield, OR 97477",
        past_orders_count=past_orders,
        merchant_dispute_ratio=merchant_dispute_ratio,
    )
    return carrier, warehouse, order


def test_supervisor_routes_horizontally_to_domain_specialists():
    """Verify DisputeSupervisor dispatches each dispute reason to the dedicated specialist agent."""
    supervisor = DisputeSupervisor()

    def _disp(reason: DisputeReason) -> PayPalDisputeResource:
        return PayPalDisputeResource(
            dispute_id=f"PP-{reason.value}",
            create_time="2026-10-18T10:00:00Z",
            dispute_stage=DisputeStage.CLAIM,
            dispute_reason=reason,
            dispute_amount=Money(currency_code="USD", value="100.00"),
        )

    assert isinstance(
        supervisor.route_specialist(_disp(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED)),
        INRAgent,
    )
    assert isinstance(
        supervisor.route_specialist(_disp(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED)),
        SNADAgent,
    )
    assert isinstance(supervisor.route_specialist(_disp(DisputeReason.UNAUTHORISED)), FraudAgent)
    assert isinstance(
        supervisor.route_specialist(_disp(DisputeReason.CANCELED_RECURRING_BILLING)), BillingAgent
    )


@pytest.mark.asyncio
async def test_universal_defense_policy_defends_micro_claim_under_15():
    """
    Seller Rights First Policy: Never concede a micro-claim (<$15, e.g. $5.00)
    when PayPal §11 proof of delivery exists.
    """
    supervisor = DisputeSupervisor()
    dispute = PayPalDisputeResource(
        dispute_id="PP-D-MICRO-5",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="5.00"),
    )
    carrier, warehouse, order = _make_base_telemetry(amount=5.00)
    compliance = SellerProtectionComplianceEngine().audit_dispute(dispute, carrier, order)

    decision = await supervisor.evaluate_dispute(
        dispute=dispute,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
        compliance=compliance,
    )

    assert decision.specialist_agent == "INRAgent"
    assert decision.persona_mode == PersonaMode.ADVERSARIAL_LEGAL_DEFENSE.value
    assert decision.seller_rights_met is True
    assert decision.recommended_action == ArbitrationAction.PROVIDE_EVIDENCE
    assert "§11" in decision.rebuttal_statement


@pytest.mark.asyncio
async def test_inr_agent_stage_aware_personas():
    """INRAgent switches between Customer Diplomat (INQUIRY) and Adversarial Legal Defense (CLAIM)."""
    supervisor = DisputeSupervisor()
    carrier, warehouse, order = _make_base_telemetry(amount=120.00)

    inquiry_dispute = PayPalDisputeResource(
        dispute_id="PP-INR-INQ",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.INQUIRY,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="120.00"),
    )
    comp_inq = SellerProtectionComplianceEngine().audit_dispute(inquiry_dispute, carrier, order)
    dec_inq = await supervisor.evaluate_dispute(
        dispute=inquiry_dispute,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
        compliance=comp_inq,
    )
    assert dec_inq.persona_mode == PersonaMode.CUSTOMER_DIPLOMAT.value
    assert dec_inq.recommended_action == ArbitrationAction.SEND_MESSAGE
    assert dec_inq.customer_message is not None
    assert "delivery concierge" in dec_inq.customer_message.lower()


@pytest.mark.asyncio
async def test_snad_agent_weight_delta_and_rma_vs_defect_offer():
    """SNADAgent defends 0.0% weight delta with RMA enforcement; concedes/offers 50% on weight failure."""
    supervisor = DisputeSupervisor()

    # 1. Valid 0.0% weight delta + serial + QA at CLAIM -> PROVIDE_EVIDENCE
    carrier, warehouse, order = _make_base_telemetry(
        amount=220.00, weight_delta=0.0, qa_passed=True
    )
    snad_claim = PayPalDisputeResource(
        dispute_id="PP-SNAD-PASS",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED,
        dispute_amount=Money(currency_code="USD", value="220.00"),
    )
    dec_pass = await supervisor.evaluate_dispute(
        dispute=snad_claim,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
    )
    assert dec_pass.specialist_agent == "SNADAgent"
    assert dec_pass.seller_rights_met is True
    assert dec_pass.recommended_action == ArbitrationAction.PROVIDE_EVIDENCE
    assert "RMA" in dec_pass.rebuttal_statement

    # 2. Failed weight delta (18.5%) at INQUIRY -> MAKE_OFFER with 50% courtesy refund
    _, bad_wh, order2 = _make_base_telemetry(amount=200.00, weight_delta=18.5, qa_passed=False)
    snad_inq = PayPalDisputeResource(
        dispute_id="PP-SNAD-FAIL-INQ",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.INQUIRY,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED,
        dispute_amount=Money(currency_code="USD", value="200.00"),
    )
    dec_fail = await supervisor.evaluate_dispute(
        dispute=snad_inq,
        carrier=carrier,
        warehouse=bad_wh,
        order=order2,
        dispute_fee=15.0,
    )
    assert dec_fail.specialist_agent == "SNADAgent"
    assert dec_fail.persona_mode == PersonaMode.CUSTOMER_DIPLOMAT.value
    assert dec_fail.seller_rights_met is False
    assert dec_fail.recommended_action == ArbitrationAction.MAKE_OFFER
    assert dec_fail.offer_amount == 100.00  # 50% courtesy refund


@pytest.mark.asyncio
async def test_fraud_agent_ce3_liability_shift_and_family_inquiry_prompt():
    """FraudAgent applies Visa CE 3.0 at CLAIM and prompts family check at INQUIRY."""
    supervisor = DisputeSupervisor()
    carrier, warehouse, order = _make_base_telemetry(amount=180.00, past_orders=5)
    ce3 = VisaCompellingEvidenceEngine().evaluate_ce3_eligibility(order=order)

    # CLAIM stage -> CE 3.0 liability shift
    fraud_claim = PayPalDisputeResource(
        dispute_id="PP-FRAUD-CE3",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.UNAUTHORISED,
        dispute_amount=Money(currency_code="USD", value="180.00"),
    )
    dec_claim = await supervisor.evaluate_dispute(
        dispute=fraud_claim,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
        ce3=ce3,
    )
    assert dec_claim.specialist_agent == "FraudAgent"
    assert dec_claim.seller_rights_met is True
    assert dec_claim.win_probability >= 0.95
    assert dec_claim.recommended_action == ArbitrationAction.PROVIDE_EVIDENCE
    assert "COMPELLING EVIDENCE 3.0" in dec_claim.rebuttal_statement

    # INQUIRY stage -> Customer Diplomat asks buyer to check with family/household
    fraud_inq = PayPalDisputeResource(
        dispute_id="PP-FRAUD-INQ",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.INQUIRY,
        dispute_reason=DisputeReason.UNAUTHORISED,
        dispute_amount=Money(currency_code="USD", value="180.00"),
    )
    dec_inq = await supervisor.evaluate_dispute(
        dispute=fraud_inq,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
        ce3=ce3,
    )
    assert dec_inq.persona_mode == PersonaMode.CUSTOMER_DIPLOMAT.value
    assert dec_inq.recommended_action == ArbitrationAction.SEND_MESSAGE
    assert dec_inq.customer_message is not None
    assert "household" in dec_inq.customer_message.lower()


@pytest.mark.asyncio
async def test_billing_agent_saas_clickwrap_vs_grace_period():
    """BillingAgent defends active post-cancellation SaaS usage and concedes inside grace window."""
    supervisor = DisputeSupervisor()
    carrier, warehouse, order = _make_base_telemetry(amount=79.00)

    # 1. Valid Clickwrap + Post-Cancellation Logins/API Calls -> DEFEND
    active_billing = BillingTelemetryInfo(
        order_id=order.order_id,
        subscription_id="SUB-SAAS-991",
        clickwrap_assent_verified=True,
        clickwrap_assent_timestamp="2026-10-01T09:00:00Z",
        clickwrap_ip_address="24.130.88.12",
        cancellation_within_grace_period=False,
        post_cancellation_login_timestamps=["2026-10-15T12:00:00Z"],
        post_cancellation_api_requests=110,
        active_sessions_count=2,
        last_active_ip="24.130.88.12",
    )
    bill_claim = PayPalDisputeResource(
        dispute_id="PP-BILL-DEFEND",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.CANCELED_RECURRING_BILLING,
        dispute_amount=Money(currency_code="USD", value="79.00"),
    )
    dec_defend = await supervisor.evaluate_dispute(
        dispute=bill_claim,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
        billing=active_billing,
    )
    assert dec_defend.specialist_agent == "BillingAgent"
    assert dec_defend.seller_rights_met is True
    assert dec_defend.recommended_action == ArbitrationAction.PROVIDE_EVIDENCE
    assert "CLICKWRAP" in dec_defend.rebuttal_statement

    # 2. Canceled within grace period -> CONCEDE at CLAIM
    grace_billing = BillingTelemetryInfo(
        order_id=order.order_id,
        subscription_id="SUB-SAAS-GRACE",
        clickwrap_assent_verified=True,
        cancellation_within_grace_period=True,
        post_cancellation_login_timestamps=[],
        post_cancellation_api_requests=0,
        active_sessions_count=0,
    )
    dec_grace = await supervisor.evaluate_dispute(
        dispute=bill_claim,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
        billing=grace_billing,
    )
    assert dec_grace.seller_rights_met is False
    assert dec_grace.recommended_action == ArbitrationAction.ACCEPT_CLAIM


@pytest.mark.asyncio
async def test_high_risk_tenant_anomaly_triggers_hitl():
    """Merchant dispute ratio >= 1.5% triggers HITL safety gate per Section 6.1."""
    supervisor = DisputeSupervisor()
    carrier, warehouse, order = _make_base_telemetry(amount=95.00, merchant_dispute_ratio=0.018)
    dispute = PayPalDisputeResource(
        dispute_id="PP-HIGH-RATIO",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="95.00"),
    )
    compliance = SellerProtectionComplianceEngine().audit_dispute(dispute, carrier, order)

    decision = await supervisor.evaluate_dispute(
        dispute=dispute,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=30.0,
        compliance=compliance,
    )

    assert decision.hitl_flagged is True
    assert decision.recommended_action == ArbitrationAction.FLAG_FOR_HITL
    assert any("High-risk tenant anomaly alert" in r for r in decision.hitl_reasons)
