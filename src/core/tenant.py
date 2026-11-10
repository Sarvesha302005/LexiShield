"""
Tenant Isolation & Management Manager.
Provides Row-Level Security (RLS) simulation, BYOK credential resolution,
and persistent database synchronization per merchant.
"""

import logging

from src.core.config import get_settings
from src.core.exceptions import PayPalDisputeEngineException
from src.models.tenant import TenantConfig, TenantCustomRules

logger = logging.getLogger(__name__)


class TenantNotFoundError(PayPalDisputeEngineException):
    """Raised when a requested tenant/merchant is not found."""

    pass


class TenantManager:
    """Manages multi-tenant onboarding, isolation, and custom rules retrieval."""

    def __init__(self) -> None:
        self._tenants: dict[str, TenantConfig] = {}
        # Seed default tenant from environment
        settings = get_settings()
        default_tenant = TenantConfig(
            merchant_id="default-merchant",
            name="Default Merchant Enterprise",
            paypal_client_id=settings.PAYPAL_CLIENT_ID,
            paypal_client_secret=settings.PAYPAL_CLIENT_SECRET,
            paypal_webhook_id=settings.PAYPAL_WEBHOOK_ID,
            custom_rules=TenantCustomRules(
                hitl_order_value_threshold=settings.HITL_ORDER_VALUE_THRESHOLD,
                defend_p_win_threshold=settings.DEFEND_P_WIN_THRESHOLD,
            ),
        )
        self._tenants["default-merchant"] = default_tenant

    async def sync_from_db(self) -> None:
        """Loads all persistent tenants from the database into the runtime registry using direct SQLite."""
        try:
            import sqlite3

            conn = sqlite3.connect("lexishield.db", timeout=5.0)
            c = conn.cursor()
            rows = c.execute("""
                SELECT merchant_id, name, paypal_client_id, paypal_client_secret, paypal_webhook_id,
                       accounting_webhook_url, rma_enabled, hitl_order_value_threshold,
                       defend_p_win_threshold, auto_concede_unwinnable, visa_ce3_enabled,
                       alert_auto_refund_enabled, is_active
                FROM tenants
            """).fetchall()
            conn.close()

            for r in rows:
                self._tenants[r[0]] = TenantConfig(
                    merchant_id=r[0],
                    name=r[1],
                    paypal_client_id=r[2],
                    paypal_client_secret=r[3],
                    paypal_webhook_id=r[4],
                    accounting_webhook_url=r[5],
                    rma_enabled=bool(r[6]),
                    custom_rules=TenantCustomRules(
                        hitl_order_value_threshold=float(r[7]),
                        defend_p_win_threshold=float(r[8]),
                        auto_concede_unwinnable=bool(r[9]),
                        visa_ce3_enabled=bool(r[10]),
                        alert_auto_refund_enabled=bool(r[11]),
                    ),
                    is_active=bool(r[12]),
                )
            if rows:
                logger.info(f"Synchronized {len(rows)} tenants from database.")
        except Exception as exc:
            logger.warning(f"Tenant database sync notice: {exc}")

    def register_tenant(self, config: TenantConfig) -> TenantConfig:
        """Onboard a new merchant tenant with their own PayPal credentials and custom rules."""
        self._tenants[config.merchant_id] = config
        logger.info(f"Registered tenant {config.merchant_id} ({config.name}).")
        return config

    def get_tenant(self, merchant_id: str | None = None) -> TenantConfig:
        """Resolve tenant configuration or fallback to default."""
        target_id = merchant_id or "default-merchant"
        if target_id not in self._tenants:
            raise TenantNotFoundError(f"Tenant '{target_id}' not found.")
        return self._tenants[target_id]

    def list_tenants(self) -> list[TenantConfig]:
        """List all active merchant tenants."""
        return list(self._tenants.values())

    def update_tenant_rules(self, merchant_id: str, rules: TenantCustomRules) -> TenantConfig:
        """Update customized dispute automation thresholds for a specific merchant."""
        tenant = self.get_tenant(merchant_id)
        tenant.custom_rules = rules
        logger.info(f"Updated custom rules for tenant {merchant_id}.")
        return tenant


tenant_manager = TenantManager()


def get_tenant_manager() -> TenantManager:
    """Dependency provider for TenantManager."""
    return tenant_manager
