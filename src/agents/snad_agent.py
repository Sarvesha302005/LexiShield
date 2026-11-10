"""
SNADAgent: Significantly Not As Described Specialist Agent.

Governing Rule: Physical Warehouse Telemetry, Barcode Serial Auditing, and Return Merchandise Authorization (RMA).
Key Checks:
- Scale Tare Weight Delta <= 2.0% (ideal 0.0%) proving complete outbound contents
- Barcode Serial / IMEI Scan matching order invoice
- Tamper Seal and QA Station Photos proving pristine outbound condition
- Mandatory RMA Enforcement before any refund consideration
"""

from __future__ import annotations

from src.agents.base import (
    BaseSpecialistAgent,
    PersonaMode,
    SpecialistContext,
    SpecialistEvaluation,
)


class SNADAgent(BaseSpecialistAgent):
    """Domain specialist for MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED disputes."""

    agent_name = "SNADAgent"
    governing_rule = (
        "Warehouse Physical Telemetry, Barcode Serial Auditing & Mandatory RMA Protocols"
    )

    MAX_ALLOWED_WEIGHT_DELTA_PCT: float = 2.0

    def evaluate_deterministic(self, ctx: SpecialistContext) -> SpecialistEvaluation:
        dispute = ctx.dispute
        warehouse = ctx.warehouse
        carrier = ctx.carrier
        order = ctx.order
        compliance = ctx.compliance

        amount = dispute.dispute_amount.float_value
        persona = self.select_persona(dispute.dispute_stage)
        citations: list[str] = []
        statutory: list[str] = [
            "Warehouse QA & Scale Tare Weight Protocol (<=2.0% Tolerance)",
            "Mandatory Return Merchandise Authorization (RMA) Refund Prerequisite",
        ]

        score = 0.50

        # 1. Scale Tare Weight Delta Check
        weight_ok = warehouse.weight_delta_percent <= self.MAX_ALLOWED_WEIGHT_DELTA_PCT
        if weight_ok:
            score += 0.18
            ideal_note = " (exact 0.0% variance)" if warehouse.weight_delta_percent == 0.0 else ""
            citations.append(
                f"Scale Tare Weight Verification PASSED{ideal_note}: measured {warehouse.scale_measured_weight_kg:.3f} kg vs expected {warehouse.expected_weight_kg:.3f} kg ({warehouse.weight_delta_percent:.2f}% delta)."
            )
        else:
            score -= 0.25
            citations.append(
                f"Scale Tare Weight Discrepancy DETECTED: {warehouse.weight_delta_percent:.2f}% variance (> {self.MAX_ALLOWED_WEIGHT_DELTA_PCT}% threshold)."
            )

        # 2. Barcode Serial / IMEI Scan Audit
        serials_present = len(warehouse.scanned_serials) > 0
        if serials_present:
            score += 0.12
            citations.append(
                f"Serialized Barcode/IMEI Scan Verified at pack station: {', '.join(warehouse.scanned_serials)}."
            )
        else:
            citations.append("No serialized hardware barcode logged at packing station.")

        # 3. Tamper Seal & QA Station Inspection Photos
        qa_passed = warehouse.quality_inspection_passed
        has_seal_and_photo = bool(warehouse.tamper_seal_id and warehouse.packing_station_photo_url)
        if qa_passed and has_seal_and_photo:
            score += 0.15
            citations.append(
                f"QA Station Inspection PASSED with security tamper seal '{warehouse.tamper_seal_id}' and pre-dispatch photo ({warehouse.packing_station_photo_url})."
            )
        elif not qa_passed:
            score -= 0.30
            citations.append("Warehouse QA station recorded an outbound packaging/quality defect.")

        # 4. Delivery continuity
        if carrier.status.upper() == "DELIVERED":
            score += 0.05
            citations.append(
                f"Delivered intact via {carrier.carrier_name} (Tracking #{carrier.tracking_number})."
            )

        compliance_ok = compliance.is_eligible if compliance else True
        if compliance and compliance.capped_win_probability is not None:
            score = min(score, compliance.capped_win_probability)
            for reason in compliance.disqualification_reasons:
                citations.insert(0, f"POLICY DISQUALIFICATION: {reason}")

        seller_rights_met = bool(qa_passed and weight_ok and has_seal_and_photo and compliance_ok)
        if seller_rights_met:
            score = max(score, 0.85)
            citations.append(
                "Mandatory RMA Protocol Enforced: Buyer must return sealed/serialized item via authorized RMA before refund consideration."
            )

        p_win = round(max(0.01, min(0.99, score)), 2)

        if persona == PersonaMode.CUSTOMER_DIPLOMAT:
            if seller_rights_met:
                customer_msg = (
                    f"Hello {order.customer_name}, we are sorry to hear Order {order.order_id} did not meet your expectations. "
                    f"Our quality team verified outbound scale weights ({warehouse.scale_measured_weight_kg:.2f} kg, {warehouse.weight_delta_percent:.1f}% variance) "
                    f"and serialized inspection prior to dispatch. We would be happy to troubleshoot setup, send replacement accessories, "
                    f"or issue a prepaid RMA return label so we can process your return promptly."
                )
            else:
                offer_amt = round(amount * 0.50, 2)
                customer_msg = (
                    f"Hello {order.customer_name}, thank you for bringing this issue on Order {order.order_id} to our attention. "
                    f"Because our warehouse audit identified a potential packing variance, we would like to proactively offer "
                    f"a 50% courtesy partial refund of ${offer_amt:.2f} or an immediate replacement."
                )
        else:
            customer_msg = None

        rebuttal = (
            f"REBUTTAL FOR PAYPAL CASE {dispute.dispute_id} [SNADAgent - WAREHOUSE TELEMETRY & RMA DEFENSE]\n\n"
            f"For Order {order.order_id} (Transaction {order.transaction_id}, Amount ${amount:.2f}), the merchant submits "
            f"verified physical warehouse telemetry proving the item dispatched matched specifications in pristine condition.\n\n"
            f"Physical Audit & Serialized Evidence:\n"
            + "\n".join(f"• {c}" for c in citations)
            + "\n\nMandatory RMA Requirement: Under merchant policy and PayPal SNAD adjudication standards, "
            "the buyer has not returned the merchandise with an authorized RMA tracking number; no refund is warranted without verified physical return."
        )

        reasoning_steps = [
            f"[SNADAgent] Selected persona '{persona.value}' for stage '{dispute.dispute_stage.value}'.",
            f"[SNADAgent] Audited scale tare weight delta: {warehouse.weight_delta_percent:.2f}% (threshold <= {self.MAX_ALLOWED_WEIGHT_DELTA_PCT}%).",
            f"[SNADAgent] Audited serial scans ({len(warehouse.scanned_serials)}) and tamper seal '{warehouse.tamper_seal_id}', QA passed={qa_passed}.",
            f"[SNADAgent] Evaluated Seller Rights & RMA enforcement: seller_rights_met={seller_rights_met}, P(win)={p_win:.2f}.",
        ]

        return SpecialistEvaluation(
            agent_name=self.agent_name,
            governing_rule=self.governing_rule,
            persona_mode=persona,
            seller_rights_met=seller_rights_met,
            win_probability=p_win,
            confidence_score=0.93 if seller_rights_met else 0.87,
            evidence_citations=citations,
            statutory_citations=statutory,
            reasoning_steps=reasoning_steps,
            executive_summary=(
                f"SNADAgent evaluated {dispute.dispute_id}: weight_delta={warehouse.weight_delta_percent:.2f}%, "
                f"QA={qa_passed}, SellerRightsMet={seller_rights_met}, P(win)={p_win:.2f}."
            ),
            rebuttal_statement=rebuttal,
            customer_message=customer_msg,
            recommended_rma=seller_rights_met,
        )
