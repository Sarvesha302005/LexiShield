"""
Orders and Telemetry Catalog API.
Provides endpoints to list seeded Zapier customer orders, inspect carrier tracking,
and query customer purchase history for dispute simulations.
"""

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from src.core.config import get_sqlite_db_path

router = APIRouter(prefix="/orders", tags=["Orders & Zapier Telemetry"])


@router.get(
    "",
    summary="List Seeded Customer Orders",
    description="Returns all 30 Zapier-synced customer orders with carrier tracking, warehouse QC weights, and past purchase history.",
)
async def list_orders(
    search: str | None = Query(None, description="Search by customer name, email, or order ID"),
    carrier: str | None = Query(None, description="Filter by carrier name (UPS, FedEx, USPS, DHL)"),
) -> list[dict[str, Any]]:
    try:
        conn = sqlite3.connect(get_sqlite_db_path(), timeout=5.0)
        c = conn.cursor()
        query = """
            SELECT order_id, transaction_id, customer_id, customer_name, customer_email,
                   order_date, total_amount, currency, shipping_address, line_items,
                   carrier_name, tracking_number, delivery_status, delivered_date,
                   signed_by, gps_latitude, gps_longitude, scale_measured_weight_kg,
                   scanned_serials, past_orders_count, past_disputes_count, created_at
            FROM orders
            ORDER BY created_at DESC
        """
        rows = c.execute(query).fetchall()
        conn.close()
    except sqlite3.Error:
        return []

    results = []
    for r in rows:
        order = {
            "order_id": r[0],
            "transaction_id": r[1],
            "customer_id": r[2],
            "customer_name": r[3],
            "customer_email": r[4],
            "order_date": r[5],
            "total_amount": r[6],
            "currency": r[7],
            "shipping_address": r[8],
            "line_items": json.loads(r[9]) if r[9] else [],
            "carrier_name": r[10],
            "tracking_number": r[11],
            "delivery_status": r[12],
            "delivered_date": r[13],
            "signed_by": r[14],
            "gps_latitude": r[15],
            "gps_longitude": r[16],
            "scale_measured_weight_kg": r[17],
            "scanned_serials": json.loads(r[18]) if r[18] else [],
            "past_orders_count": r[19],
            "past_disputes_count": r[20],
            "created_at": r[21],
        }

        # Apply in-memory filtering
        if search:
            q = search.lower()
            match = (
                q in order["order_id"].lower()
                or q in order["customer_name"].lower()
                or q in order["customer_email"].lower()
            )
            if not match:
                continue

        if carrier and carrier.lower() not in order["carrier_name"].lower():
            continue

        results.append(order)

    return results


@router.get(
    "/{order_id}",
    summary="Get Order Telemetry Record",
    description="Fetch single order details by order_id or transaction_id.",
)
async def get_order(order_id: str) -> dict[str, Any]:
    try:
        conn = sqlite3.connect(get_sqlite_db_path(), timeout=5.0)
        c = conn.cursor()
        row = c.execute(
            """
            SELECT order_id, transaction_id, customer_id, customer_name, customer_email,
                   order_date, total_amount, currency, shipping_address, line_items,
                   carrier_name, tracking_number, delivery_status, delivered_date,
                   signed_by, gps_latitude, gps_longitude, scale_measured_weight_kg,
                   scanned_serials, past_orders_count, past_disputes_count, created_at
            FROM orders
            WHERE order_id = ? OR transaction_id = ? OR tracking_number = ?
        """,
            (order_id, order_id, order_id),
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        row = None

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found in telemetry registry.",
        )

    return {
        "order_id": row[0],
        "transaction_id": row[1],
        "customer_id": row[2],
        "customer_name": row[3],
        "customer_email": row[4],
        "order_date": row[5],
        "total_amount": row[6],
        "currency": row[7],
        "shipping_address": row[8],
        "line_items": json.loads(row[9]) if row[9] else [],
        "carrier_name": row[10],
        "tracking_number": row[11],
        "delivery_status": row[12],
        "delivered_date": row[13],
        "signed_by": row[14],
        "gps_latitude": row[15],
        "gps_longitude": row[16],
        "scale_measured_weight_kg": row[17],
        "scanned_serials": json.loads(row[18]) if row[18] else [],
        "past_orders_count": row[19],
        "past_disputes_count": row[20],
        "created_at": row[21],
    }
