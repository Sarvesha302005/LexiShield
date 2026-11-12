"""
SQLAlchemy 2.0 Declarative Models for LexiShield.
Defines persistent database schemas for Tenants, Disputes, Orders, Alerts, and Accounting Events.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """Base declarative class for all database models."""

    pass


class TenantModel(Base):
    """Persistent merchant tenant configuration and BYOK credential store."""

    __tablename__ = "tenants"

    merchant_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    paypal_client_id: Mapped[str] = mapped_column(String(200), nullable=False)
    paypal_client_secret: Mapped[str] = mapped_column(String(200), nullable=False)
    paypal_webhook_id: Mapped[str] = mapped_column(String(200), nullable=False)
    accounting_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rma_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Custom Rules & Thresholds
    hitl_order_value_threshold: Mapped[float] = mapped_column(Float, default=300.00)
    defend_p_win_threshold: Mapped[float] = mapped_column(Float, default=0.70)
    auto_concede_unwinnable: Mapped[bool] = mapped_column(Boolean, default=True)
    visa_ce3_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_auto_refund_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    disputes: Mapped[list["DisputeModel"]] = relationship(
        "DisputeModel", back_populates="tenant", cascade="all, delete-orphan"
    )


class DisputeModel(Base):
    """Persistent dispute dossier and audit trail record."""

    __tablename__ = "disputes"

    dispute_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    merchant_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("tenants.merchant_id"), index=True, nullable=False
    )
    stage: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Transaction Linkage
    seller_transaction_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Pipeline Status & Decisions
    pipeline_status: Mapped[str] = mapped_column(String(50), default="ANALYZING", index=True)
    recommended_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hitl_flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    hitl_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    hitl_reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hitl_override_action: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Evidence & Audit
    rebuttal_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_dossier_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_dossier_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paypal_api_response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Agentic Reasoning Metadata
    specialist_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    persona_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_tier_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seller_rights_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reasoning_steps: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Guardrails & Liability Shifts
    compliance_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    compliance_disqualifications: Mapped[list[str]] = mapped_column(JSON, default=list)
    visa_ce3_qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    rma_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Telemetry Snapshots
    telemetry_carrier: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    telemetry_warehouse: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    telemetry_order: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    telemetry_billing: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    audit_trail: Mapped[list[str]] = mapped_column(JSON, default=list)
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Financial Metrics
    win_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    dispute_fee_applied: Mapped[float] = mapped_column(Float, default=15.00)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationship to Tenant
    tenant: Mapped["TenantModel"] = relationship("TenantModel", back_populates="disputes")


class CustomerOrderModel(Base):
    """Customer order telemetry, shipment tracking, and warehouse QA inspection store."""

    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    transaction_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    order_date: Mapped[str] = mapped_column(String(50), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Fulfillment & Carrier Telemetry
    carrier_name: Mapped[str] = mapped_column(String(100), default="FedEx")
    tracking_number: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(50), default="DELIVERED")
    delivered_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Warehouse QC
    scale_measured_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    scanned_serials: Mapped[list[str]] = mapped_column(JSON, default=list)
    past_orders_count: Mapped[int] = mapped_column(default=0)
    past_disputes_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class PreDisputeAlertModel(Base):
    """Pre-dispute deflection alert record (Ethoca / Verifi RDR)."""

    __tablename__ = "pre_dispute_alerts"

    alert_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    arn: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_refunded: Mapped[float] = mapped_column(Float, nullable=False)
    fee_saved: Mapped[float] = mapped_column(Float, nullable=False)
    deflection_status: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class AccountingEventModel(Base):
    """Double-entry ERP journal and audit log record."""

    __tablename__ = "accounting_events"

    event_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    dispute_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entries: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
