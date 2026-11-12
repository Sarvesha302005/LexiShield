"""
Base Classes and Schemas for the Horizontal Specialist Agentic Hierarchy.

Implements:
- Stage-aware dynamic personas (`CUSTOMER_DIPLOMAT` for INQUIRY vs `ADVERSARIAL_LEGAL_DEFENSE` for CLAIM)
- Common `SpecialistContext` and `SpecialistEvaluation` models
- Integration with the 3-tier LangChain `MultiModelLLMOrchestrator`
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.models.schemas import (
    BillingTelemetryInfo,
    CarrierTrackingInfo,
    DisputeStage,
    OrderCustomerInfo,
    PayPalDisputeResource,
    WarehouseFulfillmentInfo,
)
from src.services.compliance import ComplianceAuditResult
from src.services.llm_orchestrator import MultiModelLLMOrchestrator, OrchestrationTier
from src.services.visa_ce3 import CE3QualificationResult

logger = logging.getLogger(__name__)


class PersonaMode(StrEnum):
    """Stage-aware communication persona."""

    CUSTOMER_DIPLOMAT = "CUSTOMER_DIPLOMAT"
    ADVERSARIAL_LEGAL_DEFENSE = "ADVERSARIAL_LEGAL_DEFENSE"


class SpecialistContext(BaseModel):
    """Aggregated telemetry and compliance context supplied to a specialist agent."""

    dispute: PayPalDisputeResource
    carrier: CarrierTrackingInfo
    warehouse: WarehouseFulfillmentInfo
    order: OrderCustomerInfo
    billing: BillingTelemetryInfo | None = None
    compliance: ComplianceAuditResult | None = None
    ce3: CE3QualificationResult | None = None
    dispute_fee: float = 15.00


class SpecialistEvaluation(BaseModel):
    """Structured domain analysis produced by a Horizontal Specialist Agent."""

    agent_name: str
    governing_rule: str
    persona_mode: PersonaMode
    seller_rights_met: bool
    win_probability: float = Field(..., ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.92, ge=0.0, le=1.0)
    evidence_citations: list[str] = Field(default_factory=list)
    statutory_citations: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    executive_summary: str
    rebuttal_statement: str
    customer_message: str | None = None
    recommended_rma: bool = False
    llm_tier_used: OrchestrationTier = OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC
    thought_trace: str | None = None


class BaseSpecialistAgent(ABC):
    """Abstract base class for domain-specialist horizontal dispute agents."""

    agent_name: str = "BaseSpecialistAgent"
    governing_rule: str = "PayPal Seller Protection Policy"

    def __init__(self, orchestrator: MultiModelLLMOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or MultiModelLLMOrchestrator()

    @staticmethod
    def select_persona(stage: DisputeStage) -> PersonaMode:
        """Select Customer Diplomat during INQUIRY and Adversarial Legal Defense during CLAIM+."""
        if stage == DisputeStage.INQUIRY:
            return PersonaMode.CUSTOMER_DIPLOMAT
        return PersonaMode.ADVERSARIAL_LEGAL_DEFENSE

    @abstractmethod
    def evaluate_deterministic(self, ctx: SpecialistContext) -> SpecialistEvaluation:
        """Execute deterministic domain rules, Seller Rights verification, and fallback drafting."""

    def _persona_instructions(self, persona: PersonaMode) -> str:
        if persona == PersonaMode.CUSTOMER_DIPLOMAT:
            return (
                "ACTIVE PERSONA: Customer Diplomat (INQUIRY Stage).\n"
                "- Adopt an empathetic, helpful customer-concierge tone to de-escalate before formal claim escalation.\n"
                "- Provide clear tracking, troubleshooting, or policy clarity without confrontational legalese.\n"
                "- Populate `customer_message` with a courteous outreach message."
            )
        return (
            "ACTIVE PERSONA: Adversarial Legal Defense Counsel (CLAIM Stage).\n"
            "- Adopt a formal, authoritative legal rebuttal tone aimed at PayPal/bank adjudicators.\n"
            "- Explicitly assert applicable statutory safe-harbor rules (§11, Visa CE 3.0, RMA terms, Clickwrap ToS).\n"
            "- Populate `rebuttal_statement` with a structured legal argument citing exact telemetry."
        )

    def build_prompts(
        self, ctx: SpecialistContext, baseline: SpecialistEvaluation
    ) -> tuple[str, str]:
        """Build system and human prompts for Tier 1 / Tier 2 LLM reasoning."""
        system_prompt = (
            f"You are {self.agent_name}, a specialized legal & telemetry dispute agent in LexiShield.\n"
            f"Governing Policy: {self.governing_rule}.\n\n"
            f"{self._persona_instructions(baseline.persona_mode)}\n\n"
            "First reason step-by-step inside `<thought>...</thought>` tags, verifying every statutory criterion.\n"
            "Then return ONLY a JSON object matching these keys:\n"
            "{\n"
            '  "win_probability": float (0.01 to 0.99),\n'
            '  "executive_summary": string,\n'
            '  "rebuttal_statement": string,\n'
            '  "customer_message": string or null,\n'
            '  "evidence_citations": [string],\n'
            '  "reasoning_steps": [string]\n'
            "}"
        )

        snapshot: dict[str, Any] = {
            "dispute_id": ctx.dispute.dispute_id,
            "stage": ctx.dispute.dispute_stage.value,
            "reason": ctx.dispute.dispute_reason.value,
            "amount": ctx.dispute.dispute_amount.float_value,
            "currency": ctx.dispute.dispute_amount.currency_code,
            "order_id": ctx.order.order_id,
            "transaction_id": ctx.order.transaction_id,
            "seller_rights_met": baseline.seller_rights_met,
            "baseline_p_win": baseline.win_probability,
            "statutory_citations": baseline.statutory_citations,
            "deterministic_citations": baseline.evidence_citations,
            "carrier": {
                "name": ctx.carrier.carrier_name,
                "tracking_number": ctx.carrier.tracking_number,
                "status": ctx.carrier.status,
                "delivered_date": ctx.carrier.delivered_date,
                "signed_by": ctx.carrier.signed_by,
                "gps": [ctx.carrier.gps_latitude, ctx.carrier.gps_longitude],
            },
            "warehouse": {
                "scale_kg": ctx.warehouse.scale_measured_weight_kg,
                "expected_kg": ctx.warehouse.expected_weight_kg,
                "weight_delta_percent": ctx.warehouse.weight_delta_percent,
                "scanned_serials": ctx.warehouse.scanned_serials,
                "tamper_seal_id": ctx.warehouse.tamper_seal_id,
                "qa_passed": ctx.warehouse.quality_inspection_passed,
            },
        }
        if ctx.compliance:
            snapshot["compliance"] = {
                "is_eligible": ctx.compliance.is_eligible,
                "disqualification_reasons": ctx.compliance.disqualification_reasons,
                "signature_mandate_met": ctx.compliance.signature_mandate_met,
                "avs_address_matched": ctx.compliance.avs_address_matched,
                "package_redirected": ctx.compliance.package_redirected,
            }
        if ctx.ce3:
            snapshot["visa_ce3"] = {
                "is_qualified": ctx.ce3.is_qualified,
                "matched_factors": ctx.ce3.matched_factors,
                "qualifying_count": len(ctx.ce3.qualifying_transactions),
            }
        if ctx.billing:
            snapshot["billing"] = ctx.billing.model_dump()

        user_prompt = (
            "Evaluate the following dispute telemetry context and generate the structured JSON analysis:\n"
            + json.dumps(snapshot, indent=2)
        )
        return system_prompt, user_prompt

    async def analyze(self, ctx: SpecialistContext) -> SpecialistEvaluation:
        """Run deterministic rules first, then enrich via 3-tier OpenRouter LLM orchestration."""
        baseline = self.evaluate_deterministic(ctx)
        system_prompt, user_prompt = self.build_prompts(ctx, baseline)

        llm_result = await self.orchestrator.invoke_with_fallback(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            allow_live_when_mock_client=True,
        )

        baseline.llm_tier_used = llm_result.tier_used
        baseline.thought_trace = llm_result.thought_trace

        if llm_result.payload is None:
            return baseline

        payload = llm_result.payload
        if payload.win_probability is not None:
            refined_p = max(0.01, min(0.99, float(payload.win_probability)))
            if ctx.compliance and ctx.compliance.capped_win_probability is not None:
                refined_p = min(refined_p, ctx.compliance.capped_win_probability)
            if ctx.ce3 and ctx.ce3.is_qualified:
                refined_p = max(refined_p, 0.95)
            baseline.win_probability = round(refined_p, 2)

        if payload.executive_summary:
            baseline.executive_summary = payload.executive_summary
        if payload.rebuttal_statement:
            baseline.rebuttal_statement = payload.rebuttal_statement
        if payload.customer_message is not None:
            baseline.customer_message = payload.customer_message
        if payload.evidence_citations:
            merged_citations = list(
                dict.fromkeys(baseline.evidence_citations + payload.evidence_citations)
            )
            baseline.evidence_citations = merged_citations

        combined_steps = list(
            dict.fromkeys(
                llm_result.extracted_reasoning_steps
                + payload.reasoning_steps
                + baseline.reasoning_steps
            )
        )
        baseline.reasoning_steps = combined_steps
        return baseline
