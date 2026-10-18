"""
ERP & Accounting Lifecycle Integration Service.
Dispatches double-entry ledger provisioning events (NetSuite, QuickBooks, Xero compatible).
Logs pending frozen escrow liabilities upon dispute intake, and writes off fees/inventory upon concession.
"""

import logging
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LedgerEntryType(StrEnum):
    """Accounting entry types triggered by dispute events."""

    FROZEN_FUNDS_LIABILITY = "FROZEN_FUNDS_LIABILITY"
    FUNDS_RESTORED_WIN = "FUNDS_RESTORED_WIN"
    DISPUTE_FEE_EXPENSE = "DISPUTE_FEE_EXPENSE"
    INVENTORY_WRITEOFF = "INVENTORY_WRITEOFF"


class JournalEntry(BaseModel):
    """Double-entry accounting journal line."""

    account: str
    debit: float = 0.0
    credit: float = 0.0
    description: str


class AccountingEvent(BaseModel):
    """ERP accounting event payload."""

    event_id: str
    dispute_id: str
    merchant_id: str
    order_id: str
    entry_type: LedgerEntryType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    entries: list[JournalEntry] = Field(default_factory=list)


class AccountingIntegrationService:
    """Dispatches accounting journal entries to merchant ERP/accounting systems."""

    def __init__(self) -> None:
        self._event_log: list[AccountingEvent] = []

    def get_event_log(self, merchant_id: str | None = None) -> list[AccountingEvent]:
        """Query dispatched accounting events."""
        if merchant_id:
            return [e for e in self._event_log if e.merchant_id == merchant_id]
        return self._event_log

    def log_dispute_intake_frozen_funds(
        self,
        dispute_id: str,
        merchant_id: str,
        order_id: str,
        amount: float,
    ) -> AccountingEvent:
        """
        Record frozen funds escrow liability upon dispute creation:
        Debit: PayPal Frozen Escrow Asset
        Credit: Operating Cash / Accounts Receivable
        """
        event = AccountingEvent(
            event_id=f"ACC-INTAKE-{dispute_id}",
            dispute_id=dispute_id,
            merchant_id=merchant_id,
            order_id=order_id,
            entry_type=LedgerEntryType.FROZEN_FUNDS_LIABILITY,
            entries=[
                JournalEntry(
                    account="1050-PayPal-Frozen-Escrow",
                    debit=amount,
                    description="Frozen funds escrow",
                ),
                JournalEntry(
                    account="1010-Operating-Cash", credit=amount, description="Funds held by PayPal"
                ),
            ],
        )
        self._event_log.append(event)
        logger.info(f"Logged accounting freeze for {dispute_id}: ${amount:.2f}.")
        return event

    def log_dispute_concession(
        self,
        dispute_id: str,
        merchant_id: str,
        order_id: str,
        amount: float,
        dispute_fee: float,
    ) -> AccountingEvent:
        """
        Record write-off upon claim concession or loss:
        Debit: 6100-Dispute-Fee-Expense ($15-$30)
        Debit: 5010-COGS-Dispute-Writeoff (Order amount)
        Credit: 1050-PayPal-Frozen-Escrow (Total loss)
        """
        total_loss = amount + dispute_fee
        event = AccountingEvent(
            event_id=f"ACC-LOSS-{dispute_id}",
            dispute_id=dispute_id,
            merchant_id=merchant_id,
            order_id=order_id,
            entry_type=LedgerEntryType.DISPUTE_FEE_EXPENSE,
            entries=[
                JournalEntry(
                    account="6100-Dispute-Fee-Expense",
                    debit=dispute_fee,
                    description="PayPal non-refundable dispute fee",
                ),
                JournalEntry(
                    account="5010-COGS-Dispute-Loss",
                    debit=amount,
                    description="Order refund concession write-off",
                ),
                JournalEntry(
                    account="1050-PayPal-Frozen-Escrow",
                    credit=total_loss,
                    description="Clear escrow liability",
                ),
            ],
        )
        self._event_log.append(event)
        logger.info(
            f"Logged accounting write-off for {dispute_id}: Fee=${dispute_fee:.2f}, Loss=${amount:.2f}."
        )
        return event

    def log_dispute_won(
        self,
        dispute_id: str,
        merchant_id: str,
        order_id: str,
        amount: float,
    ) -> AccountingEvent:
        """
        Record restored funds upon successful defense:
        Debit: 1010-Operating-Cash
        Credit: 1050-PayPal-Frozen-Escrow
        """
        event = AccountingEvent(
            event_id=f"ACC-WIN-{dispute_id}",
            dispute_id=dispute_id,
            merchant_id=merchant_id,
            order_id=order_id,
            entry_type=LedgerEntryType.FUNDS_RESTORED_WIN,
            entries=[
                JournalEntry(
                    account="1010-Operating-Cash",
                    debit=amount,
                    description="Unfrozen funds restored to merchant",
                ),
                JournalEntry(
                    account="1050-PayPal-Frozen-Escrow",
                    credit=amount,
                    description="Clear escrow hold",
                ),
            ],
        )
        self._event_log.append(event)
        logger.info(f"Logged accounting restoration for {dispute_id}: ${amount:.2f}.")
        return event
