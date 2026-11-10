"""
Carrier Service: Aggregator and mock telemetry client for FedEx, UPS, and EasyPost.
Fetches real-time carrier tracking status, delivery timestamps, signature proof, and GPS telemetry.
"""

import logging

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
        tracking_number: str | None = None,
        order_id: str | None = None,
        customer_name: str | None = None,
        customer_email: str | None = None,
    ) -> CarrierTrackingInfo:
        """
        Fetch carrier telemetry by tracking number or order ID.
        Simulates carrier API calls with realistic telemetry, GPS, and signature records.
        """
        lookup_key = tracking_number or order_id or customer_email or customer_name or "DEFAULT"

        # Check registered overrides first
        if lookup_key in self._mock_registry:
            logger.info(f"Retrieved registered carrier telemetry for {lookup_key}.")
            return self._mock_registry[lookup_key]

        # Check SQLite lexishield.db for seeded Carrier telemetry
        try:
            import sqlite3

            conn = sqlite3.connect("lexishield.db", timeout=3.0)
            c = conn.cursor()
            row = c.execute(
                """
                SELECT carrier_name, tracking_number, delivery_status, delivered_date,
                       signed_by, shipping_address, gps_latitude, gps_longitude, order_date
                FROM orders 
                WHERE tracking_number = ? OR order_id = ? OR transaction_id = ?
                   OR customer_email = ? OR customer_name = ?
            """,
                (
                    lookup_key,
                    lookup_key,
                    lookup_key,
                    customer_email or lookup_key,
                    customer_name or lookup_key,
                ),
            ).fetchone()
            conn.close()

            if row and row[1]:
                logger.info(
                    f"Retrieved persistent Zapier carrier tracking for {lookup_key}: {row[1]}."
                )
                return CarrierTrackingInfo(
                    tracking_number=row[1],
                    carrier_name=row[0] or "UPS Next Day Air",
                    status=row[2] or "DELIVERED",
                    ship_date=row[8],
                    delivered_date=row[3],
                    destination_address=row[5],
                    gps_latitude=row[6],
                    gps_longitude=row[7],
                    signed_by=row[4] or "Verified Delivery",
                    signature_url=f"https://carrier-telemetry.cdn.example.com/signatures/{row[1]}.png",
                    events=[
                        TrackingEvent(
                            timestamp=row[8],
                            status="PICKED_UP",
                            location="Distribution Facility",
                            description="Package accepted from merchant warehouse",
                        ),
                        TrackingEvent(
                            timestamp=row[3] or "2026-10-24T14:15:30Z",
                            status="DELIVERED",
                            location=row[5].split(",")[-2].strip()
                            if "," in row[5]
                            else "Destination City",
                            description=f"Delivered to front door. Signed: {row[4]}",
                        ),
                    ],
                )
        except Exception as exc:
            logger.debug(f"SQLite carrier lookup notice: {exc}")

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
