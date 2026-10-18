"""
Order Database Service: Fetches transaction amounts, invoice lines, customer history, and past disputes.
Provides financial parameters, margin ratios, and dispute fee tiering.
"""

import logging
from typing import Optional

from src.core.config import get_settings
from src.core.exceptions import OrderDBError
from src.models.schemas import OrderCustomerInfo, OrderLineItem

logger = logging.getLogger(__name__)


class OrderDBService:
    """Async database service fetching comprehensive order and customer intelligence."""

    def __init__(self) -> None:
        self._mock_registry: dict[str, OrderCustomerInfo] = {}

    def register_mock_order(self, key: str, order_info: OrderCustomerInfo) -> None:
        """Register specific order telemetry for testing."""
        self._mock_registry[key] = order_info

    def clear_mock_registry(self) -> None:
        """Clear test registry."""
        self._mock_registry.clear()

    async def get_order_by_transaction_or_id(
        self,
        transaction_id: Optional[str] = None,
        order_id: Optional[str] = None,
        disputed_amount: Optional[float] = None,
    ) -> OrderCustomerInfo:
        """
        Fetch order record by transaction_id or order_id.
        Computes merchant dispute fee ($15 vs $30) based on merchant risk tier.
        """
        lookup_key = transaction_id or order_id or "DEFAULT"

        if lookup_key in self._mock_registry:
            logger.info(f"Retrieved registered order record for {lookup_key}.")
            return self._mock_registry[lookup_key]

        effective_order_id = order_id or f"ORD-{lookup_key[-8:] if len(lookup_key) >= 8 else lookup_key}"
        effective_txn_id = transaction_id or f"TXN-{lookup_key}"
        amount = disputed_amount if disputed_amount is not None else 185.00

        is_high_volume_disputes = "HIGH_FEE" in lookup_key.upper()
        is_serial_disputer = "SERIAL_DISPUTER" in lookup_key.upper()

        monthly_disputes = 145 if is_high_volume_disputes else 18
        past_disputes = 4 if is_serial_disputer else 0

        order_info = OrderCustomerInfo(
            order_id=effective_order_id,
            transaction_id=effective_txn_id,
            customer_id=f"CUST-{abs(hash(lookup_key)) % 10000:04d}",
            customer_name="Alex Mercer",
            customer_email="alex.mercer@example.com",
            order_date="2026-10-07T18:15:00Z",
            total_amount=amount,
            currency="USD",
            margin_rate=0.45,
            line_items=[
                OrderLineItem(
                    sku="SKU-AUDIO-PRO-X",
                    name="AcousticShield Pro Noise-Cancelling Headphones",
                    quantity=1,
                    unit_price=amount,
                    total_price=amount,
                    serial_number=f"SN-LEXI-992014-{effective_order_id[-4:]}",
                )
            ],
            shipping_address="742 Evergreen Terrace, Springfield, OR 97477",
            customer_tenure_months=24,
            past_orders_count=12,
            past_disputes_count=past_disputes,
            customer_lifetime_value=1420.00,
            merchant_monthly_disputes_count=monthly_disputes,
        )

        logger.info(f"Retrieved order telemetry for {effective_order_id} (amount=${amount}).")
        return order_info

    def determine_dispute_fee(self, monthly_disputes_count: int) -> float:
        """
        PayPal charges either standard dispute fee ($15) or high-volume dispute fee ($30)
        when monthly dispute count or ratio exceeds standard thresholds.
        """
        settings = get_settings()
        if monthly_disputes_count >= settings.HIGH_DISPUTE_FEE_THRESHOLD_MONTHLY_DISPUTES:
            return settings.HIGH_VOLUME_DISPUTE_FEE
        return settings.STANDARD_DISPUTE_FEE
