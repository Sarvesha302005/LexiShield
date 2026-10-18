"""
Carrier Service: Aggregator and mock telemetry client for FedEx, UPS, and EasyPost.
Fetches real-time carrier tracking status, delivery timestamps, signature proof, and GPS telemetry.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.core.exceptions import CarrierTelemetryError
from src.models.schemas import CarrierTrackingInfo, TrackingEvent

logger = logging.getLogger(__name__)


class CarrierService:
    """Async client for fetching logistics tracking telemetry and proof of delivery."""

    def __init__(self) -> None:
        # Internal test registry allowing test cases to inject deterministic telemetry responses
        self._mock_registry: dict[str, CarrierTrackingInfo] = {}

    def register_mock_telemetry(self, key: str, telemetry: CarrierTrackingInfo) -> None:
        """Register specific carrier telemetry for testing deterministic edge cases."""
        self._mock_registry[key] = telemetry

    def clear_mock_registry(self) -> None:
        """Clear test registry."""
        self._mock_registry.clear()

    async def get_tracking(
        self,
        tracking_number: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> CarrierTrackingInfo:
        """
        Fetch carrier telemetry by tracking number or order ID.
        Simulates carrier API calls with realistic telemetry, GPS, and signature records.
        """
        lookup_key = tracking_number or order_id or "DEFAULT"

        # Check registered overrides first
        if lookup_key in self._mock_registry:
            logger.info(f"Retrieved registered carrier telemetry for {lookup_key}.")
            return self._mock_registry[lookup_key]

        if not tracking_number and not order_id:
            raise CarrierTelemetryError("Both tracking_number and order_id are missing.")

        # Deterministic simulation based on lookup key
        is_lost_scenario = "LOST" in lookup_key.upper() or "UNDELIVERED" in lookup_key.upper()
        is_missing_gps = "NO_GPS" in lookup_key.upper()

        if is_lost_scenario:
            logger.info(f"Simulating lost/in-transit shipment for {lookup_key}.")
            return CarrierTrackingInfo(
                tracking_number=tracking_number or f"TRK-{lookup_key}",
                carrier_name="FedEx Ground",
                status="IN_TRANSIT",
                ship_date="2026-10-10T14:30:00Z",
                delivered_date=None,
                destination_address="1234 Main St, Springfield, IL 62701",
                gps_latitude=None,
                gps_longitude=None,
                signed_by=None,
                signature_url=None,
                events=[
                    TrackingEvent(
                        timestamp="2026-10-10T14:30:00Z",
                        status="SHIPMENT_PICKED_UP",
                        location="Origin Sorting Facility, Chicago, IL",
                        description="Package received by carrier",
                    ),
                    TrackingEvent(
                        timestamp="2026-10-12T08:15:00Z",
                        status="DELAYED",
                        location="In Transit Hub, Indianapolis, IN",
                        description="Severe weather delay in transit",
                    ),
                ],
            )

        # Standard successful delivery with GPS and signature confirmation
        effective_trk = tracking_number or f"TRK-FDX-{lookup_key}"
        logger.info(f"Retrieved verified delivered carrier telemetry for {effective_trk}.")
        return CarrierTrackingInfo(
            tracking_number=effective_trk,
            carrier_name="FedEx Ground",
            status="DELIVERED",
            ship_date="2026-10-08T11:00:00Z",
            delivered_date="2026-10-12T15:22:45Z",
            destination_address="742 Evergreen Terrace, Springfield, OR 97477",
            gps_latitude=None if is_missing_gps else 44.0531,
            gps_longitude=None if is_missing_gps else -123.0182,
            signed_by="H. SIMPSON",
            signature_url="https://carrier-telemetry.cdn.example.com/signatures/fedex_98234710.png",
            events=[
                TrackingEvent(
                    timestamp="2026-10-08T11:00:00Z",
                    status="PICKED_UP",
                    location="Distribution Hub, Portland, OR",
                    description="Package received by carrier from merchant warehouse",
                ),
                TrackingEvent(
                    timestamp="2026-10-11T04:20:00Z",
                    status="OUT_FOR_DELIVERY",
                    location="Local Station, Eugene, OR",
                    description="Out for delivery on courier vehicle",
                ),
                TrackingEvent(
                    timestamp="2026-10-12T15:22:45Z",
                    status="DELIVERED",
                    location="Springfield, OR",
                    description="Delivered to front porch. Signature received from recipient.",
                ),
            ],
        )
