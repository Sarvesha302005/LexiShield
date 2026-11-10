"""
Pydantic Schemas for PayPal Webhooks, Disputes, and External Telemetry.
Complies with Pydantic v2 and PayPal REST API specifications.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DisputeStage(StrEnum):
    """Dispute progression stages in PayPal."""

    INQUIRY = "INQUIRY"
    CLAIM = "CLAIM"
    PRE_ARBITRATION = "PRE_ARBITRATION"
    ARBITRATION = "ARBITRATION"


class DisputeReason(StrEnum):
    """Common PayPal dispute reasons."""

    MERCHANDISE_OR_SERVICE_NOT_RECEIVED = "MERCHANDISE_OR_SERVICE_NOT_RECEIVED"
    MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED = "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED"
    UNAUTHORISED = "UNAUTHORISED"
    INCORRECT_AMOUNT = "INCORRECT_AMOUNT"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    CANCELED_RECURRING_BILLING = "CANCELED_RECURRING_BILLING"
    OTHER = "OTHER"


def normalize_dispute_reason(raw_reason: str | DisputeReason) -> DisputeReason:
    """Normalize incoming PayPal / simulator reason strings into canonical DisputeReason."""
    if isinstance(raw_reason, DisputeReason):
        return raw_reason
    normalized = raw_reason.strip().upper()
    if normalized in {e.value for e in DisputeReason}:
        return DisputeReason(normalized)
    if normalized in ("UNAUTHORISED_TRANSACTION", "UNAUTHORIZED_TRANSACTION", "UNAUTHORIZED"):
        return DisputeReason.UNAUTHORISED
    if "RECURRING" in normalized or "BILLING" in normalized or "SUBSCRIPTION" in normalized:
        return DisputeReason.CANCELED_RECURRING_BILLING
    if "NOT_RECEIVED" in normalized or normalized == "INR":
        return DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED
    if "NOT_AS_DESCRIBED" in normalized or normalized == "SNAD":
        return DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED
    return DisputeReason.OTHER


class DisputeStatus(StrEnum):
    """PayPal dispute processing statuses."""

    OPEN = "OPEN"
    WAITING_FOR_BUYER_RESPONSE = "WAITING_FOR_BUYER_RESPONSE"
    WAITING_FOR_SELLER_RESPONSE = "WAITING_FOR_SELLER_RESPONSE"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    OTHER = "OTHER"


class Money(BaseModel):
    """Monetary amount representation."""

    currency_code: str = Field(default="USD")
    value: str = Field(..., description="Decimal amount string, e.g. '120.00'")

    @property
    def float_value(self) -> float:
        try:
            return float(self.value)
        except ValueError:
            return 0.0


class BuyerInfo(BaseModel):
    """Customer information associated with the dispute."""

    name: str | None = None
    email: str | None = None


class DisputedTransaction(BaseModel):
    """Transaction details subject to dispute."""

    buyer_transaction_id: str | None = None
    seller_transaction_id: str | None = None
    create_time: str | None = None
    transaction_status: str | None = None
    gross_amount: Money | None = None
    invoice_number: str | None = None
    custom: str | None = None
    buyer: BuyerInfo | None = None


class PayPalDisputeResource(BaseModel):
    """PayPal Dispute Resource payload."""

    dispute_id: str
    create_time: str
    update_time: str | None = None
    disputed_transactions: list[DisputedTransaction] = Field(default_factory=list)
    dispute_amount: Money
    dispute_stage: DisputeStage = DisputeStage.INQUIRY
    dispute_reason: DisputeReason = DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED
    status: DisputeStatus = DisputeStatus.WAITING_FOR_SELLER_RESPONSE
    dispute_life_cycle_stage: str | None = None
    seller_response_due_date: str | None = None


class PayPalWebhookEvent(BaseModel):
    """Top-level PayPal Webhook Event schema."""

    id: str = Field(..., description="Unique webhook event ID")
    event_version: str = "1.0"
    create_time: str
    resource_type: str = "dispute"
    event_type: str = Field(..., description="e.g. CUSTOMER.DISPUTE.CREATED")
    summary: str | None = None
    resource: PayPalDisputeResource


# ==============================================================================
# External Telemetry Schemas
# ==============================================================================


class TrackingEvent(BaseModel):
    """Milestone event in shipment tracking."""

    timestamp: str
    status: str
    location: str
    description: str


class CarrierTrackingInfo(BaseModel):
    """Carrier telemetry data (FedEx, UPS, EasyPost)."""

    tracking_number: str
    carrier_name: str
    status: str = Field(..., description="DELIVERED, IN_TRANSIT, EXCEPTION, RETURNED")
    ship_date: str
    delivered_date: str | None = None
    destination_address: str
    gps_latitude: float | None = Field(None, description="GPS delivery coordinate lat")
    gps_longitude: float | None = Field(None, description="GPS delivery coordinate lng")
    signed_by: str | None = None
    signature_url: str | None = None
    events: list[TrackingEvent] = Field(default_factory=list)


class WarehouseFulfillmentInfo(BaseModel):
    """Outbound warehouse telemetry & packing confirmation."""

    order_id: str
    pack_timestamp: str
    warehouse_id: str
    packer_id: str
    scale_measured_weight_kg: float
    expected_weight_kg: float
    weight_delta_percent: float
    scanned_barcodes: list[str] = Field(default_factory=list)
    scanned_serials: list[str] = Field(default_factory=list)
    tamper_seal_id: str
    packing_station_photo_url: str
    quality_inspection_passed: bool = True


class OrderLineItem(BaseModel):
    """Item row in an order."""

    sku: str
    name: str
    quantity: int
    unit_price: float
    total_price: float
    serial_number: str | None = None


class OrderCustomerInfo(BaseModel):
    """Order database snapshot and customer account metrics."""

    order_id: str
    transaction_id: str
    customer_id: str
    customer_name: str
    customer_email: str
    order_date: str
    total_amount: float
    currency: str = "USD"
    margin_rate: float = Field(default=0.40, description="Gross profit margin rate (0.0 - 1.0)")
    line_items: list[OrderLineItem] = Field(default_factory=list)
    shipping_address: str
    customer_tenure_months: int = 12
    past_orders_count: int = 5
    past_disputes_count: int = 0
    customer_lifetime_value: float = 650.00
    merchant_monthly_disputes_count: int = 25
    merchant_dispute_ratio: float = Field(
        default=0.004,
        description="Trailing merchant dispute-to-sales ratio (e.g. 0.004 = 0.4%)",
    )
    avs_match: str = Field(
        default="Y/Y",
        description="Address Verification System match code at authorization (e.g. 'Y/Y', 'N/N')",
    )
    cvv_match: bool = Field(
        default=True,
        description="Card Verification Value match at authorization",
    )
    checkout_ip: str = Field(
        default="198.51.100.42",
        description="Buyer IP address captured at checkout",
    )
    device_fingerprint: str = Field(
        default="DEV-FINGERPRINT-LEXI-8841",
        description="Device fingerprint hash captured at checkout",
    )


class BillingTelemetryInfo(BaseModel):
    """SaaS subscription assent, cancellation policy window, and server session telemetry."""

    order_id: str
    subscription_id: str | None = None
    clickwrap_assent_verified: bool = True
    clickwrap_assent_timestamp: str | None = None
    clickwrap_ip_address: str | None = None
    tos_version: str = "2026.1-SaaS-Enterprise"
    alleged_cancellation_date: str | None = None
    cancellation_within_grace_period: bool = False
    post_cancellation_login_timestamps: list[str] = Field(default_factory=list)
    post_cancellation_api_requests: int = 0
    active_sessions_count: int = 0
    last_active_ip: str | None = None


# ==============================================================================
# Internal Engine State & API Schemas
# ==============================================================================


class PipelineExecutionStatus(StrEnum):
    """Dispute processing pipeline status."""

    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    DEFENDED = "DEFENDED"
    CONCEDED = "CONCEDED"
    DE_ESCALATED = "DE_ESCALATED"
    FLAGGED_HITL = "FLAGGED_HITL"
    OVERRIDDEN = "OVERRIDDEN"
    FAILED = "FAILED"
    RESOLVED = "RESOLVED"


class DisputeRecord(BaseModel):
    """Engine record storing telemetry, decisions, and history for a dispute."""

    dispute_id: str
    stage: DisputeStage
    reason: DisputeReason
    amount: float
    currency: str = "USD"
    seller_transaction_id: str | None = None
    order_id: str | None = None
    customer_email: str | None = None
    pipeline_status: PipelineExecutionStatus = PipelineExecutionStatus.PENDING
    win_probability: float | None = None
    expected_value: float | None = None
    dispute_fee_applied: float | None = None
    recommended_action: str | None = None
    action_taken: str | None = None
    hitl_flagged: bool = False
    hitl_reasons: list[str] = Field(default_factory=list)
    hitl_reviewed_by: str | None = None
    hitl_override_action: str | None = None
    rebuttal_statement: str | None = None
    pdf_dossier_path: str | None = None
    pdf_dossier_sha256: str | None = None
    paypal_api_response: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    merchant_id: str = "default-merchant"
    compliance_eligible: bool | None = None
    compliance_disqualifications: list[str] = Field(default_factory=list)
    visa_ce3_qualified: bool | None = None
    rma_number: str | None = None
    specialist_agent: str | None = None
    persona_mode: str | None = None
    llm_tier_used: str | None = None
    seller_rights_met: bool | None = None
    reasoning_steps: list[str] = Field(default_factory=list)
    telemetry_carrier: CarrierTrackingInfo | None = None
    telemetry_warehouse: WarehouseFulfillmentInfo | None = None
    telemetry_order: OrderCustomerInfo | None = None
    telemetry_billing: BillingTelemetryInfo | None = None
    audit_trail: list[str] = Field(default_factory=list)


class HITLOverrideRequest(BaseModel):
    """Payload to override or approve a dispute held in the HITL queue."""

    reviewer_id: str
    action: str = Field(..., description="'DEFEND', 'CONCEDE', 'SEND_MESSAGE', or 'MAKE_OFFER'")
    override_reason: str
    adjusted_message: str | None = None
    adjusted_offer_amount: float | None = None


class DisputeStatsSummary(BaseModel):
    """Dispute engine aggregate performance metrics."""

    total_disputes: int
    defended_count: int
    conceded_count: int
    de_escalated_count: int
    hitl_queue_count: int
    total_disputed_amount: float
    total_expected_value: float
    estimated_dispute_fees_avoided: float
    average_win_probability: float
