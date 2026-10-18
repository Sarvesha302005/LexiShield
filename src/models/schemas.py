"""
Pydantic Schemas for PayPal Webhooks, Disputes, and External Telemetry.
Complies with Pydantic v2 and PayPal REST API specifications.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class DisputeStage(str, Enum):
    """Dispute progression stages in PayPal."""
    INQUIRY = "INQUIRY"
    CLAIM = "CLAIM"
    PRE_ARBITRATION = "PRE_ARBITRATION"
    ARBITRATION = "ARBITRATION"


class DisputeReason(str, Enum):
    """Common PayPal dispute reasons."""
    MERCHANDISE_OR_SERVICE_NOT_RECEIVED = "MERCHANDISE_OR_SERVICE_NOT_RECEIVED"
    MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED = "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED"
    UNAUTHORISED = "UNAUTHORISED"
    INCORRECT_AMOUNT = "INCORRECT_AMOUNT"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    CANCELED_RECURRING_BILLING = "CANCELED_RECURRING_BILLING"
    OTHER = "OTHER"


class DisputeStatus(str, Enum):
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
    name: Optional[str] = None
    email: Optional[str] = None


class DisputedTransaction(BaseModel):
    """Transaction details subject to dispute."""
    buyer_transaction_id: Optional[str] = None
    seller_transaction_id: Optional[str] = None
    create_time: Optional[str] = None
    transaction_status: Optional[str] = None
    gross_amount: Optional[Money] = None
    invoice_number: Optional[str] = None
    custom: Optional[str] = None
    buyer: Optional[BuyerInfo] = None


class PayPalDisputeResource(BaseModel):
    """PayPal Dispute Resource payload."""
    dispute_id: str
    create_time: str
    update_time: Optional[str] = None
    disputed_transactions: list[DisputedTransaction] = Field(default_factory=list)
    dispute_amount: Money
    dispute_stage: DisputeStage = DisputeStage.INQUIRY
    dispute_reason: DisputeReason = DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED
    status: DisputeStatus = DisputeStatus.WAITING_FOR_SELLER_RESPONSE
    dispute_life_cycle_stage: Optional[str] = None
    seller_response_due_date: Optional[str] = None


class PayPalWebhookEvent(BaseModel):
    """Top-level PayPal Webhook Event schema."""
    id: str = Field(..., description="Unique webhook event ID")
    event_version: str = "1.0"
    create_time: str
    resource_type: str = "dispute"
    event_type: str = Field(..., description="e.g. CUSTOMER.DISPUTE.CREATED")
    summary: Optional[str] = None
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
    delivered_date: Optional[str] = None
    destination_address: str
    gps_latitude: Optional[float] = Field(None, description="GPS delivery coordinate lat")
    gps_longitude: Optional[float] = Field(None, description="GPS delivery coordinate lng")
    signed_by: Optional[str] = None
    signature_url: Optional[str] = None
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
    serial_number: Optional[str] = None


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


# ==============================================================================
# Internal Engine State & API Schemas
# ==============================================================================

class PipelineExecutionStatus(str, Enum):
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
    seller_transaction_id: Optional[str] = None
    order_id: Optional[str] = None
    customer_email: Optional[str] = None
    pipeline_status: PipelineExecutionStatus = PipelineExecutionStatus.PENDING
    win_probability: Optional[float] = None
    expected_value: Optional[float] = None
    dispute_fee_applied: Optional[float] = None
    recommended_action: Optional[str] = None
    action_taken: Optional[str] = None
    hitl_flagged: bool = False
    hitl_reasons: list[str] = Field(default_factory=list)
    hitl_reviewed_by: Optional[str] = None
    hitl_override_action: Optional[str] = None
    rebuttal_statement: Optional[str] = None
    pdf_dossier_path: Optional[str] = None
    paypal_api_response: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    telemetry_carrier: Optional[CarrierTrackingInfo] = None
    telemetry_warehouse: Optional[WarehouseFulfillmentInfo] = None
    telemetry_order: Optional[OrderCustomerInfo] = None
    audit_trail: list[str] = Field(default_factory=list)


class HITLOverrideRequest(BaseModel):
    """Payload to override or approve a dispute held in the HITL queue."""
    reviewer_id: str
    action: str = Field(..., description="'DEFEND', 'CONCEDE', 'SEND_MESSAGE', or 'MAKE_OFFER'")
    override_reason: str
    adjusted_message: Optional[str] = None
    adjusted_offer_amount: Optional[float] = None


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
