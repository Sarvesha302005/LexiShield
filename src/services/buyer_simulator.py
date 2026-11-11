"""
Simulated buyer for demonstrating buyer <-> merchant communication on a dispute.

The buyer's first message comes from a template chosen by the dispute reason; every later buyer
message is written by the LLM role-playing the buyer, after reading the merchant's latest reply.
"""

from __future__ import annotations

import logging

from src.models.schemas import DisputeReason, DisputeRecord
from src.services.llm_orchestrator import MultiModelLLMOrchestrator, OrchestrationTier

logger = logging.getLogger(__name__)

# Plain-English issue descriptions, used in templates and in the buyer persona prompt.
REASON_DESCRIPTIONS: dict[DisputeReason, str] = {
    DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED: "the item never arrived",
    DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED: "the item is not as described",
    DisputeReason.UNAUTHORISED: "the buyer does not recognise the charge",
    DisputeReason.INCORRECT_AMOUNT: "the buyer was charged the wrong amount",
    DisputeReason.DUPLICATE_TRANSACTION: "the buyer was charged twice",
    DisputeReason.CANCELED_RECURRING_BILLING: "the buyer cancelled a subscription but was still billed",
    DisputeReason.OTHER: "a problem with the order",
}

# First buyer message for each issue type. Placeholders: {item}, {order}, {amount}.
FIRST_MESSAGE_TEMPLATES: dict[DisputeReason, str] = {
    DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED: (
        "Hi, I ordered {item} (order {order}) but it never arrived. The tracking says it was delivered, "
        "but there's nothing at my address. Can you help me find out what happened?"
    ),
    DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED: (
        "Hi, the {item} I received from order {order} doesn't match the description on your listing. "
        "It isn't what I paid {amount} for, and I'd like this resolved."
    ),
    DisputeReason.UNAUTHORISED: (
        "Hello, I don't recognise a charge of {amount} from your store on my PayPal account. "
        "I didn't make this purchase and want to know what it's for."
    ),
    DisputeReason.INCORRECT_AMOUNT: (
        "Hi, I was charged {amount} for order {order}, which is more than the price shown at checkout. "
        "Can you check this and correct the charge?"
    ),
    DisputeReason.DUPLICATE_TRANSACTION: (
        "Hi, I was charged twice for the same order ({order}). Please look into the duplicate {amount} charge."
    ),
    DisputeReason.CANCELED_RECURRING_BILLING: (
        "Hi, I cancelled my subscription, but I was still billed {amount}. "
        "Please make sure the subscription is stopped and look into this charge."
    ),
    DisputeReason.OTHER: (
        "Hi, I have a problem with order {order} and opened a case with PayPal. Can you help me sort it out?"
    ),
}

# Used when no model is available, so the demo conversation can still continue.
FOLLOW_UP_FALLBACK = "Thanks for getting back to me. I'll check on my side and reply here shortly."


def _order_details(record: DisputeRecord) -> tuple[str, str, str]:
    order = record.telemetry_order
    item = order.line_items[0].name if order and order.line_items else "my order"
    order_id = record.order_id or (order.order_id if order else None) or record.dispute_id
    return item, order_id, f"${record.amount:,.2f}"


def first_buyer_message(record: DisputeRecord) -> str:
    """The buyer's opening message, chosen by issue type."""
    template = FIRST_MESSAGE_TEMPLATES.get(
        record.reason, FIRST_MESSAGE_TEMPLATES[DisputeReason.OTHER]
    )
    item, order_id, amount = _order_details(record)
    return template.format(item=item, order=order_id, amount=amount)


async def next_buyer_message(
    record: DisputeRecord, orchestrator: MultiModelLLMOrchestrator
) -> tuple[str, str]:
    """
    Writes the buyer's next reply with the LLM, after reading the conversation so far.
    Returns (message, tier_used); falls back to a neutral follow-up when no model answers.
    """
    order = record.telemetry_order
    buyer_name = order.customer_name if order and order.customer_name else "the buyer"
    item, order_id, amount = _order_details(record)
    issue = REASON_DESCRIPTIONS.get(record.reason, REASON_DESCRIPTIONS[DisputeReason.OTHER])
    history = "\n".join(
        f"{'BUYER' if m.sender == 'BUYER' else 'MERCHANT'}: {m.content}"
        for m in record.messages[-10:]
    )

    system_prompt = (
        f"You are role-playing {buyer_name}, a buyer who opened a PayPal dispute because {issue}. "
        "This is a demonstration of realistic buyer and merchant communication. Write the buyer's next "
        "message in reply to the merchant's latest message. Keep it to 1-3 natural sentences and stay "
        "consistent with what the buyer said earlier. React to what the merchant actually said: you may "
        "be reassured and agree to close the case, remain unhappy, ask a follow-up question, or share new "
        "information. Do not invent order details beyond the facts given. Reply with JSON only."
    )
    user_prompt = (
        f"Facts: order {order_id}, item {item}, amount {amount}.\n\n"
        f"Conversation so far:\n{history}\n\n"
        """Return exactly: {"customer_message": "<the buyer's next message>"}"""
    )

    result = await orchestrator.invoke_with_fallback(system_prompt, user_prompt)
    for reason in result.fallback_reasons:
        logger.warning(f"Simulated buyer reply for {record.dispute_id}: {reason}")
    text = (result.payload.customer_message or "").strip() if result.payload else ""
    if text:
        return text, result.tier_used.value
    return FOLLOW_UP_FALLBACK, OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC.value
