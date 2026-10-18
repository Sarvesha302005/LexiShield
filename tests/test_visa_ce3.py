"""
Unit tests for Visa Compelling Evidence 3.0 (CE 3.0) Engine.
Validates 2+ historical transaction lookback (120-365 days), matching IP/device & shipping address.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.schemas import OrderCustomerInfo
from src.services.visa_ce3 import HistoricalTransaction, VisaCompellingEvidenceEngine


@pytest.fixture
def ce3_engine():
    return VisaCompellingEvidenceEngine()


@pytest.fixture
def base_order():
    return OrderCustomerInfo(
        order_id="ORD-CE3-TARGET",
        transaction_id="TXN-CE3-TARGET",
        customer_id="CUST-CE3-999",
        customer_name="Alex Mercer",
        customer_email="alex@example.com",
        order_date="2026-10-18T10:00:00Z",
        total_amount=175.00,
        shipping_address="742 Evergreen Terrace, Springfield, OR 97477",
        past_orders_count=5,
    )


def test_ce3_qualification_success(ce3_engine, base_order):
    """
    Test successful Visa CE 3.0 qualification:
    Merchant provides 2 undisputed transactions (180 & 260 days old) matching IP & address.
    """
    now = datetime.now(UTC)
    history = [
        HistoricalTransaction(
            transaction_id="TXN-PRIOR-01",
            order_date=(now - timedelta(days=180)).isoformat(),
            amount=150.00,
            ip_address="198.51.100.42",
            device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
            customer_id=base_order.customer_id,
            shipping_address=base_order.shipping_address,
            was_disputed=False,
        ),
        HistoricalTransaction(
            transaction_id="TXN-PRIOR-02",
            order_date=(now - timedelta(days=260)).isoformat(),
            amount=210.00,
            ip_address="198.51.100.42",
            device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
            customer_id=base_order.customer_id,
            shipping_address=base_order.shipping_address,
            was_disputed=False,
        ),
    ]
    ce3_engine.register_customer_ledger(base_order.customer_id, history)

    result = ce3_engine.evaluate_ce3_eligibility(
        order=base_order,
        dispute_created_time=now,
        current_ip="198.51.100.42",
        current_device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
    )

    assert result.is_qualified is True
    assert len(result.qualifying_transactions) == 2
    assert "IP_ADDRESS" in result.matched_factors
    assert "SHIPPING_ADDRESS" in result.matched_factors
    assert "LIABILITY SHIFT CLAIM" in result.liability_shift_statement


def test_ce3_disqualification_too_recent_order(ce3_engine, base_order):
    """
    Test CE 3.0 disqualification:
    Transactions newer than 120 days old do not qualify under Visa rules.
    """
    now = datetime.now(UTC)
    history = [
        HistoricalTransaction(
            transaction_id="TXN-RECENT-01",
            order_date=(now - timedelta(days=45)).isoformat(),  # 45 days old (< 120 days)
            amount=150.00,
            ip_address="198.51.100.42",
            device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
            customer_id=base_order.customer_id,
            shipping_address=base_order.shipping_address,
            was_disputed=False,
        ),
        HistoricalTransaction(
            transaction_id="TXN-RECENT-02",
            order_date=(now - timedelta(days=70)).isoformat(),  # 70 days old (< 120 days)
            amount=180.00,
            ip_address="198.51.100.42",
            device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
            customer_id=base_order.customer_id,
            shipping_address=base_order.shipping_address,
            was_disputed=False,
        ),
    ]
    ce3_engine.register_customer_ledger(base_order.customer_id, history)

    result = ce3_engine.evaluate_ce3_eligibility(
        order=base_order,
        dispute_created_time=now,
        current_ip="198.51.100.42",
        current_device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
    )

    assert result.is_qualified is False
    assert len(result.qualifying_transactions) == 0


def test_ce3_disqualification_previously_disputed(ce3_engine, base_order):
    """
    Test CE 3.0 disqualification:
    Historical transactions that were themselves disputed cannot be used to establish liability shift.
    """
    now = datetime.now(UTC)
    history = [
        HistoricalTransaction(
            transaction_id="TXN-DISPUTED-01",
            order_date=(now - timedelta(days=200)).isoformat(),
            amount=150.00,
            ip_address="198.51.100.42",
            device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
            customer_id=base_order.customer_id,
            shipping_address=base_order.shipping_address,
            was_disputed=True,  # Disputed previously
        ),
        HistoricalTransaction(
            transaction_id="TXN-VALID-02",
            order_date=(now - timedelta(days=220)).isoformat(),
            amount=180.00,
            ip_address="198.51.100.42",
            device_fingerprint="DEV-FINGERPRINT-LEXI-8841",
            customer_id=base_order.customer_id,
            shipping_address=base_order.shipping_address,
            was_disputed=False,
        ),
    ]
    ce3_engine.register_customer_ledger(base_order.customer_id, history)

    result = ce3_engine.evaluate_ce3_eligibility(order=base_order, dispute_created_time=now)
    assert result.is_qualified is False  # Only 1 qualifying, needs 2
