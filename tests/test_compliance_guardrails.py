"""
Unit tests for PayPal Seller Protection Compliance & Policy Guardrails.
Validates $750+ signature mandate, AVS address checks, and package redirection detection.
"""

import pytest

from src.models.schemas import (
    CarrierTrackingInfo,
    DisputeReason,
    DisputeStage,
    Money,
    OrderCustomerInfo,
    PayPalDisputeResource,
    TrackingEvent,
)
from src.services.compliance import SellerProtectionComplianceEngine


@pytest.fixture
def compliance_engine():
    return SellerProtectionComplianceEngine()


def test_750_signature_mandate_violation(compliance_engine):
    """
    Test PayPal $750+ Mandate:
    Tangible order >= $750 with no signature confirmation fails Seller Protection,
    caps win probability at 0.05.
    """
    dispute = PayPalDisputeResource(
        dispute_id="PP-D-HIGH-SIG-FAIL",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="850.00"),  # >= $750
    )
    carrier = CarrierTrackingInfo(
        tracking_number="TRK-NOSIG-850",
        carrier_name="FedEx Ground",
        status="DELIVERED",
        ship_date="2026-10-10T10:00:00Z",
        delivered_date="2026-10-14T12:00:00Z",
        destination_address="100 Main St, Seattle, WA 98101",
        signed_by=None,  # No signature
    )
    order = OrderCustomerInfo(
        order_id="ORD-850",
        transaction_id="TXN-850",
        customer_id="CUST-850",
        customer_name="Jordan Bell",
        customer_email="jordan@example.com",
        order_date="2026-10-09T10:00:00Z",
        total_amount=850.00,
        shipping_address="100 Main St, Seattle, WA 98101",
    )

    result = compliance_engine.audit_dispute(dispute=dispute, carrier=carrier, order=order)

    assert result.is_eligible is False
    assert result.signature_mandate_met is False
    assert result.capped_win_probability == 0.05
    assert any("750+ Mandate Violated" in r for r in result.disqualification_reasons)


def test_750_signature_mandate_passed(compliance_engine):
    """Test tangible order >= $750 with valid signature passes compliance."""
    dispute = PayPalDisputeResource(
        dispute_id="PP-D-HIGH-SIG-PASS",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="950.00"),
    )
    carrier = CarrierTrackingInfo(
        tracking_number="TRK-SIG-950",
        carrier_name="FedEx Express",
        status="DELIVERED",
        ship_date="2026-10-10T10:00:00Z",
        delivered_date="2026-10-12T14:30:00Z",
        destination_address="100 Main St, Seattle, WA 98101",
        signed_by="J. BELL",  # Signature verified
    )
    order = OrderCustomerInfo(
        order_id="ORD-950",
        transaction_id="TXN-950",
        customer_id="CUST-950",
        customer_name="Jordan Bell",
        customer_email="jordan@example.com",
        order_date="2026-10-09T10:00:00Z",
        total_amount=950.00,
        shipping_address="100 Main St, Seattle, WA 98101",
    )

    result = compliance_engine.audit_dispute(dispute=dispute, carrier=carrier, order=order)

    assert result.is_eligible is True
    assert result.signature_mandate_met is True
    assert result.capped_win_probability is None


def test_post_purchase_package_redirection_disqualifies(compliance_engine):
    """
    Test Package Redirection:
    If parcel was rerouted with carrier mid-transit, Seller Protection is voided.
    """
    dispute = PayPalDisputeResource(
        dispute_id="PP-D-REDIRECT-01",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.CLAIM,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="200.00"),
    )
    carrier = CarrierTrackingInfo(
        tracking_number="TRK-REDIR-200",
        carrier_name="UPS Ground",
        status="DELIVERED",
        ship_date="2026-10-10T10:00:00Z",
        delivered_date="2026-10-14T11:00:00Z",
        destination_address="456 Secondary Ave, Tacoma, WA (Redirected)",
        signed_by="C. SMITH",
        events=[
            TrackingEvent(
                timestamp="2026-10-12T08:00:00Z",
                status="REROUTED",
                location="Hub",
                description="Customer requested package redirect to alternate pickup location",
            )
        ],
    )
    order = OrderCustomerInfo(
        order_id="ORD-200",
        transaction_id="TXN-200",
        customer_id="CUST-200",
        customer_name="Chris Smith",
        customer_email="chris@example.com",
        order_date="2026-10-09T10:00:00Z",
        total_amount=200.00,
        shipping_address="123 Original St, Seattle, WA 98101",
    )

    result = compliance_engine.audit_dispute(dispute=dispute, carrier=carrier, order=order)

    assert result.is_eligible is False
    assert result.package_redirected is True
    assert result.capped_win_probability == 0.05
    assert any("Redirection Detected" in r for r in result.disqualification_reasons)
