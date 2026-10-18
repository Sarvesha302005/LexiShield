"""
PayPal Seller Protection Compliance & Policy Guardrails Service.
Enforces strict $750+ signature mandates, AVS address verification, package redirection detection,
and category-specific evidence templates (INR, SNAD, Digital Goods).
"""

import logging
import re

from pydantic import BaseModel, Field

from src.models.schemas import (
    CarrierTrackingInfo,
    DisputeReason,
    OrderCustomerInfo,
    PayPalDisputeResource,
)

logger = logging.getLogger(__name__)


class ComplianceAuditResult(BaseModel):
    """Compliance audit evaluation of a dispute under PayPal Seller Protection terms."""

    is_eligible: bool = Field(
        ..., description="True if dispute meets PayPal Seller Protection criteria"
    )
    disqualification_reasons: list[str] = Field(default_factory=list)
    signature_mandate_met: bool = Field(
        default=True,
        description="True if tangible order >= $750 has verified signature confirmation",
    )
    avs_address_matched: bool = Field(
        default=True,
        description="True if delivered address matches the PayPal transaction shipping address",
    )
    package_redirected: bool = Field(
        default=False,
        description="True if parcel was redirected/rerouted post-dispatch with the carrier",
    )
    dispute_category_type: str = Field(
        default="INR",
        description="'INR' (Item Not Received), 'SNAD' (Significantly Not As Described), or 'DIGITAL_GOODS'",
    )
    recommended_evidence_template: str = Field(
        ...,
        description="Template identifier used by ReportLab PDF compiler",
    )
    capped_win_probability: float | None = Field(
        default=None,
        description="If disqualified by strict policy rule, caps P(win) (e.g. 0.05)",
    )


class SellerProtectionComplianceEngine:
    """Enforces official PayPal Seller Protection guidelines and disqualification gates."""

    SIGNATURE_MANDATE_THRESHOLD: float = 750.00

    def normalize_address(self, address: str) -> str:
        """Normalize address string for fuzzy comparison (lowercase, strip punctuation)."""
        cleaned = re.sub(r"[^\w\s]", "", address.lower())
        tokens = cleaned.split()
        return " ".join(tokens)

    def check_address_match(self, order_addr: str, carrier_addr: str) -> tuple[bool, bool]:
        """
        Check if carrier delivery address matches order shipping address.
        Returns (is_matched, is_redirected).
        """
        norm_order = self.normalize_address(order_addr)
        norm_carrier = self.normalize_address(carrier_addr)

        # Basic token overlap check
        order_tokens = set(norm_order.split())
        carrier_tokens = set(norm_carrier.split())
        intersection = order_tokens.intersection(carrier_tokens)

        # If carrier explicitly has redirect keyword in address or tracking
        is_redirected = (
            "redirect" in norm_carrier
            or "reroute" in norm_carrier
            or "held at location" in norm_carrier
        )
        match_ratio = len(intersection) / max(len(order_tokens), 1)
        is_matched = match_ratio >= 0.50 and not is_redirected

        return is_matched, is_redirected

    def audit_dispute(
        self,
        dispute: PayPalDisputeResource,
        carrier: CarrierTrackingInfo,
        order: OrderCustomerInfo,
    ) -> ComplianceAuditResult:
        """
        Audit dispute against PayPal Seller Protection rules:
        1. $750+ Signature Mandate for Item Not Received (INR)
        2. AVS Exact Address Match & Post-Purchase Redirection
        3. SNAD / Digital Goods Exclusion Handling
        """
        amount = dispute.dispute_amount.float_value
        reason = dispute.dispute_reason
        disqualifications: list[str] = []
        capped_p: float | None = None

        # 1. Category Classification
        if reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED:
            category_type = "INR"
            template = "TEMPLATE_INR_LOGISTICS"
        elif reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED:
            category_type = "SNAD"
            template = "TEMPLATE_SNAD_QUALITY_ASSURANCE"
        else:
            category_type = "OTHER"
            template = "TEMPLATE_STANDARD_COMMERCIAL"

        # Check for Digital Goods in line items
        is_digital = any(
            "DIGITAL" in item.sku.upper() or "LICENSE" in item.sku.upper()
            for item in order.line_items
        )
        if is_digital:
            category_type = "DIGITAL_GOODS"
            template = "TEMPLATE_DIGITAL_ENTITLEMENT"

        # 2. $750+ Signature Mandate Enforcement
        sig_met = True
        if category_type == "INR" and amount >= self.SIGNATURE_MANDATE_THRESHOLD:
            has_signature = bool(carrier.signed_by and carrier.signed_by.strip())
            if not has_signature or carrier.status != "DELIVERED":
                sig_met = False
                msg = (
                    f"PayPal $750+ Mandate Violated: Disputed amount is ${amount:.2f} (>= ${self.SIGNATURE_MANDATE_THRESHOLD:.2f}) "
                    f"but carrier telemetry lacks verified signature confirmation."
                )
                disqualifications.append(msg)
                capped_p = 0.05  # Defense cannot succeed under Seller Protection policy
                logger.warning(f"Dispute {dispute.dispute_id}: {msg}")

        # 3. AVS Exact Address Match & Redirection
        addr_matched, redirected = self.check_address_match(
            order_addr=order.shipping_address,
            carrier_addr=carrier.destination_address,
        )

        # Check tracking events for rerouting
        for event in carrier.events:
            desc = event.description.lower()
            if "redirect" in desc or "rerouted" in desc or "customer requested hold" in desc:
                redirected = True
                break

        if redirected:
            msg = (
                "Post-Purchase Package Redirection Detected: Parcel was rerouted with the carrier "
                "to an unconfirmed address. PayPal Seller Protection is voided upon buyer redirection."
            )
            disqualifications.append(msg)
            capped_p = 0.05
            logger.warning(f"Dispute {dispute.dispute_id}: {msg}")
        elif not addr_matched and category_type == "INR":
            msg = f"Address Mismatch: Delivered address '{carrier.destination_address}' does not match order address '{order.shipping_address}'."
            disqualifications.append(msg)
            if capped_p is None or capped_p > 0.20:
                capped_p = 0.20

        is_eligible = len(disqualifications) == 0

        return ComplianceAuditResult(
            is_eligible=is_eligible,
            disqualification_reasons=disqualifications,
            signature_mandate_met=sig_met,
            avs_address_matched=addr_matched,
            package_redirected=redirected,
            dispute_category_type=category_type,
            recommended_evidence_template=template,
            capped_win_probability=capped_p,
        )
