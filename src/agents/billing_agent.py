"""
BillingAgent: Canceled Recurring and Subscription Specialist Agent.

Governing Rule: Clickwrap SaaS Contract Assent, Cancellation Policy Windows, and Telemetry Usage Logs.
Key Checks:
- Clickwrap Assent: digital audit trail of Terms of Service acceptance at checkout
- Active Telemetry Post-Cancellation: cloud server login timestamps, API requests, active sessions
- Grace Period Compliance: verifies whether cancellation fell inside refund grace period
"""

from __future__ import annotations

from src.agents.base import (
    BaseSpecialistAgent,
    PersonaMode,
    SpecialistContext,
    SpecialistEvaluation,
)
from src.models.schemas import BillingTelemetryInfo, DisputeReason


class BillingAgent(BaseSpecialistAgent):
    """Domain specialist for CANCELED_RECURRING_BILLING and billing/subscription disputes."""

    agent_name = "BillingAgent"
    governing_rule = (
        "Clickwrap SaaS Contract Assent, Cancellation Policy Windows & Server Usage Telemetry"
    )

    def evaluate_deterministic(self, ctx: SpecialistContext) -> SpecialistEvaluation:
        dispute = ctx.dispute
        order = ctx.order
        billing = ctx.billing or BillingTelemetryInfo(order_id=order.order_id)

        amount = dispute.dispute_amount.float_value
        persona = self.select_persona(dispute.dispute_stage)
        citations: list[str] = []
        statutory: list[str] = [
            "Electronic Signatures (ESIGN / Clickwrap ToS Assent)",
            "Subscription Cancellation Window & Active Usage Telemetry Policy",
        ]

        # Duplicate transaction check: merchants do not have Seller Rights to keep accidental double charges
        if dispute.dispute_reason == DisputeReason.DUPLICATE_TRANSACTION:
            citations.append(
                f"Duplicate transaction detected for Order {order.order_id}; refund/concession recommended to preserve dispute ratio."
            )
            p_win = 0.15
            offer_amt = round(amount * 0.50, 2)
            customer_msg = (
                f"Hello {order.customer_name}, thank you for contacting us regarding Order {order.order_id}. "
                f"We apologize for the duplicate billing charge and would like to issue a 50% courtesy adjustment (${offer_amt:.2f}) or full duplicate reversal."
                if persona == PersonaMode.CUSTOMER_DIPLOMAT
                else None
            )
            return SpecialistEvaluation(
                agent_name=self.agent_name,
                governing_rule=self.governing_rule,
                persona_mode=persona,
                seller_rights_met=False,
                win_probability=p_win,
                confidence_score=0.95,
                evidence_citations=citations,
                statutory_citations=statutory,
                reasoning_steps=[
                    f"[BillingAgent] Identified duplicate transaction on {dispute.dispute_id}; Seller Rights failed -> concede/refund."
                ],
                executive_summary=f"BillingAgent flagged duplicate charge on {dispute.dispute_id}; P(win)={p_win:.2f}.",
                rebuttal_statement=f"Billing review for {dispute.dispute_id} indicates duplicate transaction; merchant recommends concession.",
                customer_message=customer_msg,
            )

        score = 0.45

        # 1. Clickwrap Assent Audit
        assent_ok = billing.clickwrap_assent_verified
        if assent_ok:
            score += 0.20
            citations.append(
                f"Clickwrap Assent Verified: Buyer accepted {billing.tos_version} at {billing.clickwrap_assent_timestamp or order.order_date} from IP {billing.clickwrap_ip_address or order.checkout_ip}."
            )
        else:
            score -= 0.25
            citations.append(
                "Clickwrap Assent Missing: No digital contract acceptance audit trail found at checkout."
            )

        # 2. Grace Period Compliance
        outside_grace = not billing.cancellation_within_grace_period
        if outside_grace:
            score += 0.10
            citations.append(
                f"Cancellation Window Audit: Alleged cancellation ({billing.alleged_cancellation_date or 'N/A'}) falls outside the refundable grace period."
            )
        else:
            score -= 0.35
            citations.append(
                f"Grace Period Triggered: Cancellation ({billing.alleged_cancellation_date or 'N/A'}) was received within the contractual refund grace window."
            )

        # 3. Active Server Telemetry Post-Cancellation
        has_post_cancel_activity = (
            len(billing.post_cancellation_login_timestamps) > 0
            or billing.post_cancellation_api_requests > 0
            or billing.active_sessions_count > 0
        )
        if has_post_cancel_activity:
            score += 0.20
            citations.append(
                f"Active Post-Cancellation Telemetry: {len(billing.post_cancellation_login_timestamps)} cloud logins, "
                f"{billing.post_cancellation_api_requests} API key requests, and {billing.active_sessions_count} active sessions "
                f"recorded from IP {billing.last_active_ip or order.checkout_ip} after alleged cancellation."
            )
        else:
            score -= 0.15
            citations.append(
                "No active cloud server sessions or API requests logged post-cancellation."
            )

        seller_rights_met = bool(assent_ok and outside_grace and has_post_cancel_activity)
        if seller_rights_met:
            score = max(score, 0.88)

        p_win = round(max(0.01, min(0.99, score)), 2)

        if persona == PersonaMode.CUSTOMER_DIPLOMAT:
            if seller_rights_met:
                customer_msg = (
                    f"Hello {order.customer_name}, thank you for contacting us about subscription {billing.subscription_id or order.order_id}. "
                    f"Our records indicate your plan was actively accessed ({billing.post_cancellation_api_requests} API requests / "
                    f"{len(billing.post_cancellation_login_timestamps)} logins) under your accepted Terms ({billing.tos_version}). "
                    f"We can gladly pause your subscription, adjust your billing tier, or review our cancellation window with you."
                )
            else:
                offer_amt = round(amount * 0.50, 2)
                customer_msg = (
                    f"Hello {order.customer_name}, we reviewed your subscription cancellation request for Order {order.order_id}. "
                    f"Since the cancellation falls within our grace/inactivity window, we would like to offer an immediate "
                    f"50% courtesy refund of ${offer_amt:.2f} or process your billing cancellation."
                )
        else:
            customer_msg = None

        rebuttal = (
            f"REBUTTAL FOR PAYPAL CASE {dispute.dispute_id} [BillingAgent - SAAS CLICKWRAP & USAGE TELEMETRY DEFENSE]\n\n"
            f"For Subscription Order {order.order_id} (Transaction {order.transaction_id}, Amount ${amount:.2f}), "
            f"the merchant submits immutable clickwrap assent logs and cloud server session telemetry proving valid billing consent and continued service utilization.\n\n"
            f"Contractual & Usage Evidence:\n" + "\n".join(f"• {c}" for c in citations)
        )

        reasoning_steps = [
            f"[BillingAgent] Selected persona '{persona.value}' for stage '{dispute.dispute_stage.value}'.",
            f"[BillingAgent] Verified clickwrap assent={assent_ok} (ToS {billing.tos_version}).",
            f"[BillingAgent] Checked cancellation grace period: within_grace={billing.cancellation_within_grace_period}.",
            f"[BillingAgent] Audited post-cancellation telemetry: logins={len(billing.post_cancellation_login_timestamps)}, api_calls={billing.post_cancellation_api_requests}.",
            f"[BillingAgent] SellerRightsMet={seller_rights_met}, P(win)={p_win:.2f}.",
        ]

        return SpecialistEvaluation(
            agent_name=self.agent_name,
            governing_rule=self.governing_rule,
            persona_mode=persona,
            seller_rights_met=seller_rights_met,
            win_probability=p_win,
            confidence_score=0.94 if seller_rights_met else 0.89,
            evidence_citations=citations,
            statutory_citations=statutory,
            reasoning_steps=reasoning_steps,
            executive_summary=(
                f"BillingAgent evaluated {dispute.dispute_id}: assent={assent_ok}, "
                f"post_cancel_usage={has_post_cancel_activity}, SellerRightsMet={seller_rights_met}, P(win)={p_win:.2f}."
            ),
            rebuttal_statement=rebuttal,
            customer_message=customer_msg,
            recommended_rma=False,
        )
