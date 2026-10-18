"""
Unit tests for AI Arbitration Logic, Win Probability, Expected Value, and Decision Branching.
"""

import pytest
from src.core.config import get_settings
from src.models.arbitration import ArbitrationAction, ArbitrationDecision
from src.models.schemas import (
    CarrierTrackingInfo,
    DisputeReason,
    DisputeStage,
    Money,
    OrderCustomerInfo,
    OrderLineItem,
    PayPalDisputeResource,
    WarehouseFulfillmentInfo,
)
from src.services.llm_arbitrator import LLMArbitrator
from src.services.order import OrderDBService


@pytest.fixture
def arbitrator():
    return LLMArbitrator()


@pytest.fixture
def order_service():
    return OrderDBService()


def test_calculate_expected_value(arbitrator):
    """
    Test EV calculation:
    E[V] = P(win) * OrderValue - (1 - P(win)) * (OrderValue + DisputeFee)
    """
    order_val = 100.0
    fee = 15.0

    # 100% win probability -> EV = 100.00
    ev_100 = arbitrator.calculate_expected_value(order_val, 1.0, fee)
    assert ev_100 == 100.00

    # 0% win probability -> EV = -(100 + 15) = -115.00
    ev_0 = arbitrator.calculate_expected_value(order_val, 0.0, fee)
    assert ev_0 == -115.00

    # 70% win probability:
    # EV = 0.70 * 100 - 0.30 * 115 = 70.0 - 34.5 = 35.50
    ev_70 = arbitrator.calculate_expected_value(order_val, 0.70, fee)
    assert ev_70 == 35.50

    # With high-volume $30 fee:
    # EV = 0.70 * 100 - 0.30 * 130 = 70.0 - 39.0 = 31.00
    ev_70_high_fee = arbitrator.calculate_expected_value(order_val, 0.70, 30.0)
    assert ev_70_high_fee == 31.00


def test_dispute_fee_tiering(order_service):
    """Test standard $15 vs high-volume $30 dispute fee tiering."""
    settings = get_settings()
    assert order_service.determine_dispute_fee(10) == settings.STANDARD_DISPUTE_FEE
    assert order_service.determine_dispute_fee(99) == settings.STANDARD_DISPUTE_FEE
    assert order_service.determine_dispute_fee(100) == settings.HIGH_VOLUME_DISPUTE_FEE
    assert order_service.determine_dispute_fee(250) == settings.HIGH_VOLUME_DISPUTE_FEE


def test_inquiry_stage_decision_branching(arbitrator):
    """Verify INQUIRY stage routes to de-escalation actions (SEND_MESSAGE or MAKE_OFFER)."""
    # High confidence inquiry -> SEND_MESSAGE
    action, hitl, _ = arbitrator.apply_decision_logic(
        stage=DisputeStage.INQUIRY,
        order_value=80.0,
        p_win=0.85,
        expected_value=50.0,
        dispute_fee=15.0,
        citations=["Delivered"],
    )
    assert action == ArbitrationAction.SEND_MESSAGE
    assert hitl is False

    # Low confidence inquiry -> MAKE_OFFER (partial refund)
    action_low, hitl_low, _ = arbitrator.apply_decision_logic(
        stage=DisputeStage.INQUIRY,
        order_value=80.0,
        p_win=0.40,
        expected_value=-20.0,
        dispute_fee=15.0,
        citations=["Delayed"],
    )
    assert action_low == ArbitrationAction.MAKE_OFFER
    assert hitl_low is False


def test_claim_stage_defense_branching(arbitrator):
    """Verify CLAIM stage with P(win) >= 0.70 defends via PROVIDE_EVIDENCE."""
    action, hitl, _ = arbitrator.apply_decision_logic(
        stage=DisputeStage.CLAIM,
        order_value=150.0,
        p_win=0.80,
        expected_value=75.0,
        dispute_fee=15.0,
        citations=["Delivered", "GPS Verified"],
    )
    assert action == ArbitrationAction.PROVIDE_EVIDENCE
    assert hitl is False


def test_claim_stage_concession_branching(arbitrator):
    """Verify CLAIM stage with P(win) < 0.70 concedes via ACCEPT_CLAIM."""
    action, hitl, _ = arbitrator.apply_decision_logic(
        stage=DisputeStage.CLAIM,
        order_value=50.0,
        p_win=0.35,
        expected_value=-25.0,
        dispute_fee=15.0,
        citations=["Lost in transit"],
    )
    assert action == ArbitrationAction.ACCEPT_CLAIM
    assert hitl is False


def test_hitl_edge_case_order_value_over_300(arbitrator):
    """Verify Order Value > $300 triggers mandatory HITL review."""
    action, hitl, reasons = arbitrator.apply_decision_logic(
        stage=DisputeStage.CLAIM,
        order_value=450.0,  # Exceeds $300 threshold
        p_win=0.90,
        expected_value=300.0,
        dispute_fee=15.0,
        citations=["Delivered"],
    )
    assert action == ArbitrationAction.FLAG_FOR_HITL
    assert hitl is True
    assert any("High order value" in r for r in reasons)


def test_hitl_edge_case_borderline_pwin(arbitrator):
    """Verify 0.60 <= P(win) < 0.75 triggers HITL review."""
    action, hitl, reasons = arbitrator.apply_decision_logic(
        stage=DisputeStage.CLAIM,
        order_value=120.0,
        p_win=0.68,  # Borderline within [0.60, 0.75)
        expected_value=45.0,
        dispute_fee=15.0,
        citations=["Delivered"],
    )
    assert action == ArbitrationAction.FLAG_FOR_HITL
    assert hitl is True
    assert any("Borderline win probability" in r for r in reasons)


@pytest.mark.asyncio
async def test_arbitrate_full_synthesis(arbitrator):
    """Test full telemetry synthesis pipeline producing structured ArbitrationDecision."""
    dispute = PayPalDisputeResource(
        dispute_id="PP-D-TEST-SYNTH-01",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="150.00"),
    )
    carrier = CarrierTrackingInfo(
        tracking_number="TRK-FEDEX-992211",
        carrier_name="FedEx Ground",
        status="DELIVERED",
        ship_date="2026-10-10T10:00:00Z",
        delivered_date="2026-10-13T14:20:00Z",
        destination_address="123 Main St, Austin, TX",
        gps_latitude=30.2672,
        gps_longitude=-97.7431,
        signed_by="J. DOE",
    )
    warehouse = WarehouseFulfillmentInfo(
        order_id="ORD-992211",
        pack_timestamp="2026-10-09T08:00:00Z",
        warehouse_id="WH-CENTRAL-01",
        packer_id="P-101",
        scale_measured_weight_kg=1.45,
        expected_weight_kg=1.45,
        weight_delta_percent=0.0,
        scanned_barcodes=["UPC-001"],
        scanned_serials=["SN-AUDIO-99"],
        tamper_seal_id="SEAL-01",
        packing_station_photo_url="https://example.com/photo.jpg",
        quality_inspection_passed=True,
    )
    order = OrderCustomerInfo(
        order_id="ORD-992211",
        transaction_id="TXN-992211",
        customer_id="C-1",
        customer_name="John Doe",
        customer_email="john@example.com",
        order_date="2026-10-08T12:00:00Z",
        total_amount=150.00,
        shipping_address="123 Main St, Austin, TX",
    )

    decision: ArbitrationDecision = await arbitrator.arbitrate(
        dispute=dispute,
        carrier=carrier,
        warehouse=warehouse,
        order=order,
        dispute_fee=15.0,
    )

    assert decision.dispute_id == "PP-D-TEST-SYNTH-01"
    assert decision.win_probability >= 0.70
    assert decision.expected_value > 0.0
    assert decision.recommended_action == ArbitrationAction.PROVIDE_EVIDENCE
    assert len(decision.evidence_citations) > 0
    assert "REBUTTAL FOR PAYPAL CASE" in decision.rebuttal_statement
