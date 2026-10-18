"""
Automated Return Merchandise Authorization (RMA) & Prepaid Label Service.
Integrates with carrier APIs (EasyPost/Shippo mock) to generate prepaid return labels
and monitor inbound return delivery scans before issuing refunds.
"""

import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RMADetails(BaseModel):
    """Return Merchandise Authorization details and tracking telemetry."""

    rma_number: str
    order_id: str
    dispute_id: str
    carrier_name: str = "USPS Priority Return"
    return_tracking_number: str
    prepaid_label_url: str
    status: str = (
        "LABEL_ISSUED"  # "LABEL_ISSUED", "IN_TRANSIT", "DELIVERED_RECEIVED", "INSPECTED_PASSED"
    )
    created_at: str = "2026-10-18T12:00:00Z"
    delivered_at: str | None = None


class RMAManager:
    """Manages automated return label generation and inspection gates."""

    def __init__(self) -> None:
        self._rma_store: dict[str, RMADetails] = {}

    def generate_return_label(
        self,
        order_id: str,
        dispute_id: str,
        customer_name: str,
    ) -> RMADetails:
        """
        Generate a prepaid carrier return label for customer return settlement.
        """
        rma_num = f"RMA-{order_id[-6:] if len(order_id) >= 6 else '1001'}"
        trk = f"9400111899223344{abs(hash(order_id)) % 10000:04d}"

        rma = RMADetails(
            rma_number=rma_num,
            order_id=order_id,
            dispute_id=dispute_id,
            carrier_name="USPS Return Service",
            return_tracking_number=trk,
            prepaid_label_url=f"https://labels.shipping-carrier.cdn.example.com/rma/{rma_num}_label.pdf",
            status="LABEL_ISSUED",
        )
        self._rma_store[dispute_id] = rma
        logger.info(f"Generated return label for dispute {dispute_id}: RMA={rma_num}, Trk={trk}.")
        return rma

    def get_rma(self, dispute_id: str) -> RMADetails | None:
        """Fetch RMA details for a dispute."""
        return self._rma_store.get(dispute_id)

    def mark_inbound_delivery_received(self, dispute_id: str) -> RMADetails | None:
        """
        Update status when return parcel is delivered to warehouse and passes QA inspection.
        Unlocks final refund issuance.
        """
        rma = self._rma_store.get(dispute_id)
        if rma:
            rma.status = "INSPECTED_PASSED"
            rma.delivered_at = "2026-10-18T16:00:00Z"
            logger.info(f"RMA {rma.rma_number} delivered and inspection passed for {dispute_id}.")
        return rma
