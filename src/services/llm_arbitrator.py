"""
Backward-compatible Arbitration Facade delegating to the Horizontal Agentic AI Hierarchy
(`DisputeSupervisor` -> `INRAgent` / `SNADAgent` / `FraudAgent` / `BillingAgent`).
"""

from __future__ import annotations

import logging

from src.agents.supervisor import DisputeSupervisor
from src.core.config import get_settings
from src.models.arbitration import ArbitrationAction, ArbitrationDecision
from src.models.schemas import (
    BillingTelemetryInfo,
    CarrierTrackingInfo,
    DisputeStage,
    OrderCustomerInfo,
    PayPalDisputeResource,
    WarehouseFulfillmentInfo,
)
from src.services.compliance import ComplianceAuditResult
from src.services.visa_ce3 import CE3QualificationResult

logger = logging.getLogger(__name__)


class LLMArbitrator:
    """
    Compatibility facade wrapping `DisputeSupervisor` and horizontal domain specialist agents.
    Preserves legacy `calculate_expected_value`, `evaluate_heuristic_win_probability`,
    `apply_decision_logic`, and `arbitrate` entrypoints.
    """

    def __init__(self, supervisor: DisputeSupervisor | None = None) -> None:
        self.settings = get_settings()
        self.supervisor = supervisor or DisputeSupervisor(settings=self.settings)

    def calculate_expected_value(
        self,
        order_value: float,
        p_win: float,
        dispute_fee: float,
    ) -> float:
        """Delegate E[V] calculation to DisputeSupervisor."""
        return self.supervisor.calculate_expected_value(
            order_value=order_value,
            p_win=p_win,
            dispute_fee=dispute_fee,
        )

    def evaluate_heuristic_win_probability(
        self,
        dispute: PayPalDisputeResource,
        carrier: CarrierTrackingInfo,
        warehouse: WarehouseFulfillmentInfo,
        order: OrderCustomerInfo,
        billing: BillingTelemetryInfo | None = None,
    ) -> tuple[float, list[str]]:
        """Delegate deterministic specialist evaluation for backward-compatible callers."""
        from src.agents.base import SpecialistContext

        specialist = self.supervisor.route_specialist(dispute=dispute, order=order)
        ctx = SpecialistContext(
            dispute=dispute,
            carrier=carrier,
            warehouse=warehouse,
            order=order,
            billing=billing,
        )
        evaluation = specialist.evaluate_deterministic(ctx)
        return evaluation.win_probability, evaluation.evidence_citations

    def apply_decision_logic(
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
        """Delegate decision policy and HITL gatekeeping to DisputeSupervisor."""
        return self.supervisor.apply_decision_policy(
            stage=stage,
            order_value=order_value,
            p_win=p_win,
            expected_value=expected_value,
            dispute_fee=dispute_fee,
            citations=citations,
            seller_rights_met=seller_rights_met,
            merchant_dispute_ratio=merchant_dispute_ratio,
        )

    async def arbitrate(
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
        """Orchestrate horizontal specialist evaluation via DisputeSupervisor."""
        decision = await self.supervisor.evaluate_dispute(
            dispute=dispute,
            carrier=carrier,
            warehouse=warehouse,
            order=order,
            dispute_fee=dispute_fee,
            compliance=compliance,
            ce3=ce3,
            billing=billing,
        )
        logger.info(
            f"Arbitration complete for {dispute.dispute_id}: Specialist={decision.specialist_agent}, "
            f"Tier={decision.llm_tier_used}, Action={decision.recommended_action}, "
            f"P(win)={decision.win_probability}, EV=${decision.expected_value}, HITL={decision.hitl_flagged}."
        )
        return decision
