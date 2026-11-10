"""
FraudAgent: Unauthorized Transaction and Friendly Fraud Specialist Agent.

Governing Rule: Visa Compelling Evidence 3.0 (CE 3.0) & PayPal Unauthorized Transaction Safe Harbor.
Key Checks:
- Visa CE 3.0 Network Liability Shift: >=2 undisputed historical transactions (>120 days old)
  matching >=2 core identifiers (IP/device fingerprint + shipping address/account login ID)
- AVS (Y/Y) and CVV match at authorization
"""

from __future__ import annotations

from src.agents.base import (
    BaseSpecialistAgent,
    PersonaMode,
    SpecialistContext,
    SpecialistEvaluation,
)


class FraudAgent(BaseSpecialistAgent):
    """Domain specialist for UNAUTHORISED / Friendly Fraud disputes."""

    agent_name = "FraudAgent"
    governing_rule = (
        "Visa Compelling Evidence 3.0 (CE 3.0) & PayPal Unauthorized Transaction Safe Harbor"
    )

    def evaluate_deterministic(self, ctx: SpecialistContext) -> SpecialistEvaluation:
        dispute = ctx.dispute
        order = ctx.order
        carrier = ctx.carrier
        ce3 = ctx.ce3
        compliance = ctx.compliance

        amount = dispute.dispute_amount.float_value
        persona = self.select_persona(dispute.dispute_stage)
        citations: list[str] = []
        statutory: list[str] = ["PayPal Unauthorized Transaction Safe Harbor"]

        score = 0.45

        # 1. Visa CE 3.0 Network Liability Shift Check
        ce3_qualified = bool(ce3 and ce3.is_qualified)
        if ce3_qualified and ce3:
            score = max(score, 0.95)
            statutory.append("Visa Compelling Evidence 3.0 (Core Rule 10.4 Liability Shift)")
            citations.append(
                f"VISA CE 3.0 QUALIFIED: {len(ce3.qualifying_transactions)} historical undisputed transactions (>120 days) matched on {', '.join(ce3.matched_factors)}."
            )
        else:
            citations.append(
                "Visa CE 3.0: Insufficient (>120 day) historical undisputed matches on file."
            )

        # 2. AVS (Y/Y) and CVV Match at Authorization
        avs_full_match = order.avs_match.strip().upper() == "Y/Y"
        cvv_matched = bool(order.cvv_match)
        if avs_full_match and cvv_matched:
            score += 0.25
            statutory.append("AVS (Y/Y) & CVV Authorization Match")
            citations.append(
                f"Authorization Telemetry PASSED: Full AVS match ({order.avs_match}) and CVV verified from IP {order.checkout_ip} (Device: {order.device_fingerprint})."
            )
        else:
            score -= 0.15
            citations.append(
                f"Authorization Telemetry Weak: AVS={order.avs_match}, CVV={'MATCH' if cvv_matched else 'MISMATCH'}."
            )

        # 3. Delivery / Fulfillment Proof
        delivered = carrier.status.upper() == "DELIVERED"
        if delivered:
            score += 0.15
            citations.append(
                f"Fulfillment confirmed DELIVERED to '{carrier.destination_address}' via {carrier.carrier_name} (Tracking #{carrier.tracking_number})."
            )
        else:
            score -= 0.20
            citations.append(f"Carrier tracking status is '{carrier.status}' (not DELIVERED).")

        compliance_ok = compliance.is_eligible if compliance else True
        if compliance and compliance.capped_win_probability is not None:
            score = min(score, compliance.capped_win_probability)
            for reason in compliance.disqualification_reasons:
                citations.insert(0, f"POLICY DISQUALIFICATION: {reason}")

        # Re-assert CE 3.0 override when not explicitly disqualified by redirection
        if ce3_qualified and compliance_ok:
            score = max(score, 0.95)

        seller_rights_met = bool(
            ce3_qualified or (avs_full_match and cvv_matched and delivered and compliance_ok)
        )
        if seller_rights_met:
            score = max(score, 0.85)

        p_win = round(max(0.01, min(0.99, score)), 2)

        if persona == PersonaMode.CUSTOMER_DIPLOMAT:
            if seller_rights_met:
                customer_msg = (
                    f"Hello {order.customer_name}, we received your inquiry regarding Order {order.order_id} "
                    f"(placed on {order.order_date} for ${amount:.2f}). Our records show this purchase was authorized "
                    f"from your verified IP ({order.checkout_ip}) and device profile with matching billing details, and shipped "
                    f"via {carrier.carrier_name} (Tracking #{carrier.tracking_number}) to {order.shipping_address}. "
                    f"Please check with family or household members to see if someone placed this order on your behalf."
                )
            else:
                offer_amt = round(amount * 0.50, 2)
                customer_msg = (
                    f"Hello {order.customer_name}, thank you for alerting us regarding Order {order.order_id}. "
                    f"While our security team reviews authorization telemetry, we would like to offer a 50% courtesy "
                    f"partial refund of ${offer_amt:.2f} or assist in canceling/refunding this transaction promptly."
                )
        else:
            customer_msg = None

        ce3_block = f"\n\n{ce3.liability_shift_statement}" if ce3_qualified and ce3 else ""
        rebuttal = (
            f"REBUTTAL FOR PAYPAL CASE {dispute.dispute_id} [FraudAgent - VISA CE 3.0 & AUTHORIZATION SAFE HARBOR]\n\n"
            f"The merchant formally contests this unauthorized transaction claim for Order {order.order_id} "
            f"(Transaction {order.transaction_id}, Amount ${amount:.2f}).\n\n"
            f"Identity, Device & Network Evidence:\n"
            + "\n".join(f"• {c}" for c in citations)
            + ce3_block
        )

        reasoning_steps = [
            f"[FraudAgent] Selected persona '{persona.value}' for stage '{dispute.dispute_stage.value}'.",
            f"[FraudAgent] Checked Visa CE 3.0 qualification: qualified={ce3_qualified}.",
            f"[FraudAgent] Checked authorization telemetry: AVS={order.avs_match}, CVV={cvv_matched}, delivered={delivered}.",
            f"[FraudAgent] Evaluated liability shift standing: seller_rights_met={seller_rights_met}, P(win)={p_win:.2f}.",
        ]

        return SpecialistEvaluation(
            agent_name=self.agent_name,
            governing_rule=self.governing_rule,
            persona_mode=persona,
            seller_rights_met=seller_rights_met,
            win_probability=p_win,
            confidence_score=0.96 if ce3_qualified else 0.90,
            evidence_citations=citations,
            statutory_citations=statutory,
            reasoning_steps=reasoning_steps,
            executive_summary=(
                f"FraudAgent evaluated {dispute.dispute_id}: CE3={ce3_qualified}, "
                f"AVS={order.avs_match}, SellerRightsMet={seller_rights_met}, P(win)={p_win:.2f}."
            ),
            rebuttal_statement=rebuttal,
            customer_message=customer_msg,
            recommended_rma=False,
        )
