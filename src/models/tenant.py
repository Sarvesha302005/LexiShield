"""
Multi-Tenant SaaS Data Models and Custom Rules Engine.
Defines tenant-level credential isolation (BYOK) and merchant-specific risk tolerance settings.
"""

from pydantic import BaseModel, Field


class TenantCustomRules(BaseModel):
    """Configurable risk thresholds and automation rules per merchant."""

    hitl_order_value_threshold: float = Field(
        default=300.00,
        description="Order value threshold triggering mandatory human review",
    )
    defend_p_win_threshold: float = Field(
        default=0.70,
        description="Minimum P(win) to defend claims vs concede",
    )
    auto_concede_unwinnable: bool = Field(
        default=True,
        description="Automatically concede claims that fail mandatory policies ($750 mandate, redirection)",
    )
    visa_ce3_enabled: bool = Field(
        default=True,
        description="Enable Visa Compelling Evidence 3.0 pre-dispute matching",
    )
    alert_auto_refund_enabled: bool = Field(
        default=True,
        description="Enable zero-fee automated refunds for Ethoca/Verifi alerts",
    )


class TenantConfig(BaseModel):
    """Tenant configuration with BYOK credential management and isolation."""

    merchant_id: str = Field(..., description="Unique merchant organization identifier")
    name: str = Field(..., description="Merchant business name")
    paypal_client_id: str
    paypal_client_secret: str
    paypal_webhook_id: str
    accounting_webhook_url: str | None = None
    rma_enabled: bool = True
    custom_rules: TenantCustomRules = Field(default_factory=TenantCustomRules)
    is_active: bool = True
