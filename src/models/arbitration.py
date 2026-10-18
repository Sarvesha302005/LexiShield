"""
Pydantic Schemas for AI Arbitration, Win Probability, and Decision Reasoning.
These structured models are populated by Google Gemini 1.5 via Instructor.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ArbitrationAction(StrEnum):
    """Action recommended by the arbitration engine."""

    SEND_MESSAGE = "SEND_MESSAGE"
    MAKE_OFFER = "MAKE_OFFER"
    PROVIDE_EVIDENCE = "PROVIDE_EVIDENCE"
    ACCEPT_CLAIM = "ACCEPT_CLAIM"
    FLAG_FOR_HITL = "FLAG_FOR_HITL"


class ArbitrationDecision(BaseModel):
    """
    Arbitration layer evaluation and recommendation.
    Outputs computed win probability P(win), expected value E[V],
    and formal evidence dossier citations.
    """

    dispute_id: str = Field(..., description="Target PayPal dispute ID")
    win_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability P(win) of winning the dispute on appeal/review (0.0 to 1.0)",
    )
    expected_value: float = Field(
        ...,
        description="Calculated financial expected value E[V] of defending vs conceding",
    )
    dispute_fee_applied: float = Field(
        default=15.0,
        description="Dispute fee applied in calculation ($15.00 standard or $30.00 high volume)",
    )
    recommended_action: ArbitrationAction = Field(
        ...,
        description="Recommended operational action based on business rules and stage",
    )
    hitl_flagged: bool = Field(
        default=False,
        description="True if order value > $300 or 0.60 <= P(win) < 0.75",
    )
    hitl_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons why human-in-the-loop review was triggered",
    )
    confidence_score: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Model confidence score in the telemetry match and assessment",
    )
    executive_summary: str = Field(
        ...,
        description="Concise summary of the dispute facts, evidence match, and rationale",
    )
    rebuttal_statement: str = Field(
        ...,
        description="Formal, persuasive evidentiary rebuttal statement citing PayPal Seller Protection",
    )
    customer_message: str | None = Field(
        default=None,
        description="Proposed message for customer de-escalation in INQUIRY stage",
    )
    offer_amount: float | None = Field(
        default=None,
        description="Proposed refund/settlement offer amount for INQUIRY stage",
    )
    evidence_citations: list[str] = Field(
        default_factory=list,
        description="Concrete evidentiary bullet points (Carrier GPS, Barcode serials, Packing weight)",
    )
    reasoning_steps: list[str] = Field(
        default_factory=list,
        description="Step-by-step chain-of-thought analysis leading to the arbitration outcome",
    )
