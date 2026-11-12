"""
DisputeSupervisor: Horizontal Router, Financial Gatekeeper, Universal Defense Policy Enforcer,
and HITL Safety Gatekeeper.
"""

from __future__ import annotations

import logging

from src.agents.base import BaseSpecialistAgent, SpecialistContext, SpecialistEvaluation
from src.agents.billing_agent import BillingAgent
from src.agents.fraud_agent import FraudAgent
from src.agents.inr_agent import INRAgent
from src.agents.snad_agent import SNADAgent
from src.core.config import Settings, get_settings
from src.models.arbitration import ArbitrationAction, ArbitrationDecision
from src.models.schemas import (
    BillingTelemetryInfo,
    CarrierTrackingInfo,
    DisputeReason,
    DisputeStage,
    OrderCustomerInfo,
    PayPalDisputeResource,
    WarehouseFulfillmentInfo,
)
from src.services.compliance import ComplianceAuditResult
from src.services.llm_orchestrator import MultiModelLLMOrchestrator
from src.services.visa_ce3 import CE3QualificationResult

logger = logging.getLogger(__name__)


class DisputeSupervisor:
    """
    Top-level horizontal orchestrator in LexiShield's Agentic AI Hierarchy.
    Routes disputes to domain-specialist agents, enforces Seller Rights First universal defense,
    computes E[V], and gates high-risk/high-value/borderline cases for HITL sign-off.
    """

    def __init__(
        self,
        orchestrator: MultiModelLLMOrchestrator | None = None,
        settings: Settings | None = None,
        inr_agent: INRAgent | None = None,
        snad_agent: SNADAgent | None = None,
        fraud_agent: FraudAgent | None = None,
        billing_agent: BillingAgent | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.orchestrator = orchestrator or MultiModelLLMOrchestrator(settings=self.settings)
        self.inr_agent = inr_agent or INRAgent(orchestrator=self.orchestrator)
        self.snad_agent = snad_agent or SNADAgent(orchestrator=self.orchestrator)
        self.fraud_agent = fraud_agent or FraudAgent(orchestrator=self.orchestrator)
        self.billing_agent = billing_agent or BillingAgent(orchestrator=self.orchestrator)

    def route_specialist(
        self,
        dispute: PayPalDisputeResource,
        order: OrderCustomerInfo | None = None,
    ) -> BaseSpecialistAgent:
        """Route incoming dispute to the appropriate horizontal reason-specialist agent."""
        reason = dispute.dispute_reason
        if reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED:
            return self.inr_agent
        if reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED:
            return self.snad_agent
        if reason == DisputeReason.UNAUTHORISED:
            return self.fraud_agent
        if reason in (
            DisputeReason.CANCELED_RECURRING_BILLING,
            DisputeReason.DUPLICATE_TRANSACTION,
            DisputeReason.INCORRECT_AMOUNT,
        ):
            return self.billing_agent

        if order and any(
            "SAAS" in item.sku.upper() or "SUBSCRIPTION" in item.name.upper()
            for item in order.line_items
        ):
            return self.billing_agent
        return self.inr_agent

    @staticmethod
    def calculate_expected_value(
        order_value: float,
        p_win: float,
        dispute_fee: float,
    ) -> float:
        """
        Calculate Expected Value E[V] of defending vs conceding:
        E[V] = P(win) * OrderValue - (1 - P(win)) * (OrderValue + DisputeFee)
        """
        ev = (p_win * order_value) - ((1.0 - p_win) * (order_value + dispute_fee))
        return round(ev, 2)

    def apply_decision_policy(
        self,
        stage: DisputeStage,
        order_value: float,
        p_win: float,
        expected_value: float,
        dispute_fee: float,
        citations: list[str],
        seller_rights_met: bool | None = None,
        merchant_dispute_ratio: float = 0.004,
    ) -> tuple[ArbitrationAction, bool, list[str]]:
        """
        Enforce 'Seller Rights First' Universal Defense Policy & HITL Safety Gates:
        - HITL Gate:
          * Order value > $300.00
          * Borderline win probability: 0.60 <= P(win) < 0.75
          * High-risk tenant anomaly alert: merchant dispute ratio >= 1.5%
        - Universal Defense Policy:
          * If Seller Rights Met -> DEFEND at CLAIM (PROVIDE_EVIDENCE / FLAG_FOR_HITL) for ANY amount ($1 to $10,000+),
            or SEND_MESSAGE at INQUIRY. Never micro-concede.
          * If Seller Rights Failed -> ACCEPT_CLAIM at CLAIM or MAKE_OFFER (50% courtesy refund) at INQUIRY.
        """
        _ = expected_value, dispute_fee, citations
        hitl_reasons: list[str] = []
        is_hitl = False

        if order_value > self.settings.HITL_ORDER_VALUE_THRESHOLD:
            is_hitl = True
            hitl_reasons.append(
                f"High order value (${order_value:.2f} > ${self.settings.HITL_ORDER_VALUE_THRESHOLD:.2f})."
            )

        if self.settings.HITL_P_WIN_LOWER <= p_win < self.settings.HITL_P_WIN_UPPER:
            is_hitl = True
            hitl_reasons.append(
                f"Borderline win probability P(win)={p_win:.2f} within [{self.settings.HITL_P_WIN_LOWER}, {self.settings.HITL_P_WIN_UPPER})."
            )

        if merchant_dispute_ratio >= self.settings.HIGH_RISK_TENANT_ANOMALY_THRESHOLD:
            is_hitl = True
            hitl_reasons.append(
                f"High-risk tenant anomaly alert: dispute ratio {merchant_dispute_ratio * 100:.2f}% >= {self.settings.HIGH_RISK_TENANT_ANOMALY_THRESHOLD * 100:.2f}% threshold."
            )

        # Stage == INQUIRY
        if stage == DisputeStage.INQUIRY:
            if seller_rights_met is True:
                action = ArbitrationAction.SEND_MESSAGE
            elif seller_rights_met is False:
                action = ArbitrationAction.MAKE_OFFER
            else:
                action = (
                    ArbitrationAction.MAKE_OFFER if p_win < 0.50 else ArbitrationAction.SEND_MESSAGE
                )
        # Stage == CLAIM / PRE_ARBITRATION / ARBITRATION
        else:
            if self.settings.SELLER_RIGHTS_FIRST_ENABLED and seller_rights_met is True:
                action = ArbitrationAction.PROVIDE_EVIDENCE
            elif seller_rights_met is False:
                action = (
                    ArbitrationAction.PROVIDE_EVIDENCE
                    if p_win >= self.settings.DEFEND_P_WIN_THRESHOLD
                    else ArbitrationAction.ACCEPT_CLAIM
                )
            else:
                action = (
                    ArbitrationAction.PROVIDE_EVIDENCE
                    if p_win >= self.settings.DEFEND_P_WIN_THRESHOLD
                    else ArbitrationAction.ACCEPT_CLAIM
                )

        if is_hitl:
            return ArbitrationAction.FLAG_FOR_HITL, True, hitl_reasons

        return action, False, []

    async def evaluate_dispute(
        self,
        dispute: PayPalDisputeResource,
        carrier: CarrierTrackingInfo,
        warehouse: WarehouseFulfillmentInfo,
        order: OrderCustomerInfo,
        dispute_fee: float,
        compliance: ComplianceAuditResult | None = None,
        ce3: CE3QualificationResult | None = None,
        billing: BillingTelemetryInfo | None = None,
    ) -> ArbitrationDecision:
        """Route to specialist agent, apply financial & policy gates, and return ArbitrationDecision."""
        order_value = dispute.dispute_amount.float_value
        specialist = self.route_specialist(dispute=dispute, order=order)

        ctx = SpecialistContext(
            dispute=dispute,
            carrier=carrier,
            warehouse=warehouse,
            order=order,
            billing=billing,
            compliance=compliance,
            ce3=ce3,
            dispute_fee=dispute_fee,
        )

        logger.info(
            f"[DisputeSupervisor] Routing dispute {dispute.dispute_id} ({dispute.dispute_reason.value}) -> {specialist.agent_name}"
        )
        evaluation: SpecialistEvaluation = await specialist.analyze(ctx)

        p_win = evaluation.win_probability
        ev = self.calculate_expected_value(
            order_value=order_value,
            p_win=p_win,
            dispute_fee=dispute_fee,
        )

        action, hitl_flagged, hitl_reasons = self.apply_decision_policy(
            stage=dispute.dispute_stage,
            order_value=order_value,
            p_win=p_win,
            expected_value=ev,
            dispute_fee=dispute_fee,
            citations=evaluation.evidence_citations,
            seller_rights_met=evaluation.seller_rights_met,
            merchant_dispute_ratio=order.merchant_dispute_ratio,
        )

        offer_amt: float | None = None
        if dispute.dispute_stage == DisputeStage.INQUIRY and (
            action == ArbitrationAction.MAKE_OFFER or not evaluation.seller_rights_met
        ):
            offer_amt = round(order_value * 0.50, 2)

        supervisor_steps = [
            f"[DisputeSupervisor] Routed {dispute.dispute_id} ({dispute.dispute_reason.value}) to {evaluation.agent_name}.",
            *evaluation.reasoning_steps,
            f"[DisputeSupervisor] Computed E[V]=${ev:.2f} (Order=${order_value:.2f}, Fee=${dispute_fee:.2f}, P(win)={p_win:.2f}).",
            f"[DisputeSupervisor] Applied Seller Rights First ({evaluation.seller_rights_met}) & HITL gate (flagged={hitl_flagged}) -> {action.value}.",
        ]

        return ArbitrationDecision(
            dispute_id=dispute.dispute_id,
            win_probability=p_win,
            expected_value=ev,
            dispute_fee_applied=dispute_fee,
            recommended_action=action,
            hitl_flagged=hitl_flagged,
            hitl_reasons=hitl_reasons,
            confidence_score=evaluation.confidence_score,
            executive_summary=evaluation.executive_summary,
            rebuttal_statement=evaluation.rebuttal_statement,
            customer_message=evaluation.customer_message,
            offer_amount=offer_amt,
            evidence_citations=evaluation.evidence_citations,
            reasoning_steps=supervisor_steps,
            specialist_agent=evaluation.agent_name,
            persona_mode=evaluation.persona_mode.value,
            llm_tier_used=evaluation.llm_tier_used.value,
            thought_trace=evaluation.thought_trace,
            seller_rights_met=evaluation.seller_rights_met,
            statutory_citations=evaluation.statutory_citations,
        )
