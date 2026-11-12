"""
Comprehensive tests for Pre-Chargeback Deflection, Conversational Settlement Bot,
Multi-Tenant SaaS isolation, and ERP Accounting Lifecycle.
"""

import pytest
from httpx import AsyncClient

from src.models.schemas import (
    CarrierTrackingInfo,
    DisputeReason,
    DisputeStage,
    Money,
    OrderCustomerInfo,
    PayPalDisputeResource,
)
from src.services.accounting import AccountingIntegrationService, LedgerEntryType
from src.services.alerts import AlertNetwork, PreChargebackDeflectionEngine, PreDisputeAlert
from src.services.conversation_bot import ConversationalSettlementBot, NegotiationStep
from src.services.rma import RMAManager


@pytest.mark.asyncio
async def test_pre_chargeback_deflection_zero_fee_refund():
    """
    Test Pre-Chargeback Deflection:
    Ethoca alert processed within 20-72h lead time triggers zero-fee automated refund,
    averts formal dispute creation, and prevents dispute fees ($15-$30).
    """
    engine = PreChargebackDeflectionEngine()
    alert = PreDisputeAlert(
        alert_id="ALERT-ETHOCA-99221",
        network=AlertNetwork.ETHOCA,
        arn="ARN-88220011223344",
        transaction_id="TXN-DEFLECT-01",
        amount=140.00,
        currency="USD",
        card_last4="4242",
        cardholder_name="Jane Doe",
    )

    result = await engine.process_alert(alert=alert, auto_refund=True)

    assert result.deflection_status == "DEFLECTED_ZERO_FEE_REFUND"
    assert result.amount_refunded == 140.00
    assert result.fee_saved >= 15.00
    assert "Averted formal chargeback" in result.details


def test_conversational_settlement_bot_3_step_ladder():
    """
    Test Conversational Settlement Bot during INQUIRY:
    Turn 1: Inquire with tracking and troubleshooting
    Turn 2: Offer 50% partial refund or reshipment (per Decision Matrix)
    Turn 3: Escalate to formal arbitration
    """
    bot = ConversationalSettlementBot()
    dispute = PayPalDisputeResource(
        dispute_id="PP-D-BOT-INQ-01",
        create_time="2026-10-18T10:00:00Z",
        dispute_stage=DisputeStage.INQUIRY,
        dispute_reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        dispute_amount=Money(currency_code="USD", value="100.00"),
    )
    carrier = CarrierTrackingInfo(
        tracking_number="TRK-BOT-01",
        carrier_name="FedEx Ground",
        status="DELIVERED",
        ship_date="2026-10-10T10:00:00Z",
        destination_address="123 Oak St, Portland, OR",
    )
    order = OrderCustomerInfo(
        order_id="ORD-BOT-01",
        transaction_id="TXN-BOT-01",
        customer_id="C-BOT",
        customer_name="Sam Taylor",
        customer_email="sam@example.com",
        order_date="2026-10-09T10:00:00Z",
        total_amount=100.00,
        shipping_address="123 Oak St, Portland, OR",
    )

    # Turn 1
    step1, msg1, offer1 = bot.advance_negotiation(dispute, carrier, order)
    assert step1 == NegotiationStep.STEP_1_TROUBLESHOOTING
    assert "assist you with delivery verification" in msg1
    assert offer1 is None

    # Turn 2
    step2, msg2, offer2 = bot.advance_negotiation(
        dispute, carrier, order, incoming_buyer_message="Still haven't found it"
    )
    assert step2 == NegotiationStep.STEP_2_PARTIAL_REFUND
    assert offer2 == 50.00  # 50% partial refund of $100
    assert "50% courtesy partial refund" in msg2

    # Turn 3
    step3, msg3, offer3 = bot.advance_negotiation(
        dispute, carrier, order, incoming_buyer_message="I want a full refund"
    )
    assert step3 == NegotiationStep.STEP_3_FORMAL_ARBITRATION
    assert "formal case adjudication" in msg3
    assert offer3 is None


def test_erp_accounting_lifecycle_events():
    """
    Test ERP accounting ledger provisioning:
    - Intake: logs pending liability frozen funds
    - Win: restores unfrozen operating funds
    - Concession: logs dispute fee expense ($15/$30) and COGS write-off
    """
    service = AccountingIntegrationService()
    m_id = "merchant-acme"
    disp_id = "PP-D-ACC-01"
    ord_id = "ORD-ACC-01"
    amount = 250.00
    fee = 15.00

    # 1. Intake Frozen Funds
    ev_freeze = service.log_dispute_intake_frozen_funds(disp_id, m_id, ord_id, amount)
    assert ev_freeze.entry_type == LedgerEntryType.FROZEN_FUNDS_LIABILITY
    assert any(
        j.account == "1050-PayPal-Frozen-Escrow" and j.debit == amount for j in ev_freeze.entries
    )

    # 2. Concession Loss Write-off
    ev_loss = service.log_dispute_concession(disp_id, m_id, ord_id, amount, fee)
    assert ev_loss.entry_type == LedgerEntryType.DISPUTE_FEE_EXPENSE
    assert any(j.account == "6100-Dispute-Fee-Expense" and j.debit == fee for j in ev_loss.entries)
    assert any(j.account == "5010-COGS-Dispute-Loss" and j.debit == amount for j in ev_loss.entries)

    # 3. Won / Restoration
    ev_win = service.log_dispute_won(disp_id, m_id, ord_id, amount)
    assert ev_win.entry_type == LedgerEntryType.FUNDS_RESTORED_WIN
    assert any(j.account == "1010-Operating-Cash" and j.debit == amount for j in ev_win.entries)


def test_automated_rma_lifecycle():
    """
    Test automated Return Merchandise Authorization (RMA):
    Generates return label and monitors inbound delivery verification.
    """
    rma_mgr = RMAManager()
    rma = rma_mgr.generate_return_label(
        order_id="ORD-RMA-88",
        dispute_id="PP-D-RMA-88",
        customer_name="Morgan Reed",
    )

    assert rma.status == "LABEL_ISSUED"
    assert "9400" in rma.return_tracking_number
    assert "labels.shipping-carrier.cdn.example.com" in rma.prepaid_label_url

    # Inbound delivery scan
    delivered_rma = rma_mgr.mark_inbound_delivery_received("PP-D-RMA-88")
    assert delivered_rma.status == "INSPECTED_PASSED"


@pytest.mark.asyncio
async def test_multi_tenant_api_and_custom_rules(async_client: AsyncClient):
    """
    Test Multi-Tenant API:
    Onboard tenant with custom rules, update thresholds, and verify isolated settings.
    """
    tenant_payload = {
        "merchant_id": "tenant-brand-alpha",
        "name": "Brand Alpha Storefront",
        "paypal_client_id": "client_alpha_123",
        "paypal_client_secret": "secret_alpha_456",
        "paypal_webhook_id": "webhook_alpha_789",
        "custom_rules": {
            "hitl_order_value_threshold": 150.00,  # Lowered threshold
            "defend_p_win_threshold": 0.80,  # Stricter defense cutoff
            "visa_ce3_enabled": True,
        },
    }

    # 1. Onboard Tenant
    resp = await async_client.post("/api/v1/tenants", json=tenant_payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["merchant_id"] == "tenant-brand-alpha"
    assert created["custom_rules"]["hitl_order_value_threshold"] == 150.00

    # 2. Get Tenant
    get_resp = await async_client.get("/api/v1/tenants/tenant-brand-alpha")
    assert get_resp.status_code == 200

    # 3. Update Rules
    new_rules = {
        "hitl_order_value_threshold": 200.00,
        "defend_p_win_threshold": 0.75,
        "auto_concede_unwinnable": True,
        "visa_ce3_enabled": True,
        "alert_auto_refund_enabled": True,
    }
    put_resp = await async_client.put("/api/v1/tenants/tenant-brand-alpha/rules", json=new_rules)
    assert put_resp.status_code == 200
    assert put_resp.json()["custom_rules"]["hitl_order_value_threshold"] == 200.00
