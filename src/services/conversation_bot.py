"""
Interactive Conversational Settlement Bot (Inquiry Stage).
Manages autonomous multi-turn buyer negotiation on PayPal prior to formal claim escalation.
Implements a 3-step tiered resolution ladder:
1. Inquire & provide tracking/troubleshooting (Customer Diplomat persona)
2. Offer 50% courtesy partial refund or replacement per Decision Matrix
3. Final formal settlement or arbitration handover
"""

import logging
from enum import StrEnum

from pydantic import BaseModel, Field

from src.models.schemas import CarrierTrackingInfo, OrderCustomerInfo, PayPalDisputeResource

logger = logging.getLogger(__name__)


class NegotiationStep(StrEnum):
    """Tiered resolution ladder steps."""

    STEP_1_TROUBLESHOOTING = "STEP_1_TROUBLESHOOTING"
    STEP_2_PARTIAL_REFUND = "STEP_2_PARTIAL_REFUND"
    STEP_3_FORMAL_ARBITRATION = "STEP_3_FORMAL_ARBITRATION"


class MessageEntry(BaseModel):
    """Historical message in buyer negotiation thread."""

    sender: str  # "MERCHANT", "BUYER", "PAYPAL"
    timestamp: str
    content: str


class ConversationState(BaseModel):
    """Active conversational negotiation state for an INQUIRY dispute."""

    dispute_id: str
    current_step: NegotiationStep = NegotiationStep.STEP_1_TROUBLESHOOTING
    turn_count: int = 0
    message_history: list[MessageEntry] = Field(default_factory=list)
    active_offer_amount: float | None = None
    buyer_sentiment: str = "NEUTRAL"  # "NEUTRAL", "FRUSTRATED", "COOPERATIVE"
    is_settled: bool = False


class ConversationalSettlementBot:
    """Autonomous negotiation agent operating during PayPal INQUIRY stage."""

    def __init__(self) -> None:
        self._conversations: dict[str, ConversationState] = {}

    def get_or_create_conversation(self, dispute_id: str) -> ConversationState:
        """Retrieve or initialize conversation state for a dispute."""
        if dispute_id not in self._conversations:
            self._conversations[dispute_id] = ConversationState(dispute_id=dispute_id)
        return self._conversations[dispute_id]

    def advance_negotiation(
        self,
        dispute: PayPalDisputeResource,
        carrier: CarrierTrackingInfo,
        order: OrderCustomerInfo,
        incoming_buyer_message: str | None = None,
        custom_step1_message: str | None = None,
    ) -> tuple[NegotiationStep, str, float | None]:
        """
        Evaluate conversational context and decide next action on resolution ladder:
        Returns (next_step, message_to_send, optional_offer_amount).
        """
        state = self.get_or_create_conversation(dispute.dispute_id)
        state.turn_count += 1
        order_val = dispute.dispute_amount.float_value

        if incoming_buyer_message:
            state.message_history.append(
                MessageEntry(sender="BUYER", timestamp="now", content=incoming_buyer_message)
            )

        # Step 1: Initial Troubleshooting & Tracking Proof
        if state.turn_count == 1:
            state.current_step = NegotiationStep.STEP_1_TROUBLESHOOTING
            msg = custom_step1_message or (
                f"Hello {order.customer_name}, thank you for contacting us regarding Order {order.order_id}. "
                f"Our logistics records show that package {carrier.tracking_number} was marked as {carrier.status} "
                f"by {carrier.carrier_name}. If you have not located your package or encountered an issue, please let us know "
                f"so we can assist you with delivery verification or troubleshooting."
            )
            state.message_history.append(
                MessageEntry(sender="MERCHANT", timestamp="now", content=msg)
            )
            return state.current_step, msg, None

        # Step 2: Courtesy Partial Refund Offer (50% per Universal Defense Decision Matrix)
        elif state.turn_count == 2:
            state.current_step = NegotiationStep.STEP_2_PARTIAL_REFUND
            offer_amt = round(order_val * 0.50, 2)  # 50% courtesy partial refund
            state.active_offer_amount = offer_amt
            msg = (
                f"Hello {order.customer_name}, we appreciate your patience while we investigate this. "
                f"To resolve this promptly and ensure your satisfaction, we would like to offer an immediate "
                f"50% courtesy partial refund of ${offer_amt:.2f} while keeping the order active, or alternatively "
                f"we can ship an immediate replacement unit at no cost to you. Please let us know your preference."
            )
            state.message_history.append(
                MessageEntry(sender="MERCHANT", timestamp="now", content=msg)
            )
            return state.current_step, msg, offer_amt

        # Step 3: Escalation to Formal Settlement / Arbitration
        else:
            state.current_step = NegotiationStep.STEP_3_FORMAL_ARBITRATION
            msg = (
                f"Hello {order.customer_name}, since we have been unable to reach an agreement on partial resolution, "
                f"we are providing full documentation, tracking, and warehouse telemetry to PayPal for formal case adjudication. "
                f"Our support desk remains available if you wish to contact us directly."
            )
            state.message_history.append(
                MessageEntry(sender="MERCHANT", timestamp="now", content=msg)
            )
            return state.current_step, msg, None
