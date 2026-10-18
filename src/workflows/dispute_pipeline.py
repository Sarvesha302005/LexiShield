"""
Dispute Pipeline Orchestrator: Chaining Ingestion -> Gather -> LLM -> Dispatch.
Manages end-to-end automated resolution, idempotent processing, and HITL lifecycle.
"""

import asyncio
import logging
from datetime import UTC, datetime

from src.core.config import get_settings
from src.core.exceptions import DisputeNotFoundError
from src.models.arbitration import ArbitrationAction, ArbitrationDecision
from src.models.schemas import (
    DisputeRecord,
    DisputeStage,
    DisputeStatsSummary,
    HITLOverrideRequest,
    PayPalDisputeResource,
    PayPalWebhookEvent,
    PipelineExecutionStatus,
)
from src.services.carrier import CarrierService
from src.services.llm_arbitrator import LLMArbitrator
from src.services.order import OrderDBService
from src.services.paypal_client import PayPalClient
from src.services.pdf_generator import PDFGenerator
from src.services.warehouse import WarehouseService

logger = logging.getLogger(__name__)


class DisputePipeline:
    """Enterprise orchestrator for automated dispute intake, telemetry gathering, and resolution."""

    def __init__(
        self,
        carrier_service: CarrierService | None = None,
        warehouse_service: WarehouseService | None = None,
        order_service: OrderDBService | None = None,
        llm_arbitrator: LLMArbitrator | None = None,
        pdf_generator: PDFGenerator | None = None,
        paypal_client: PayPalClient | None = None,
    ) -> None:
        self.settings = get_settings()
        self.carrier_service = carrier_service or CarrierService()
        self.warehouse_service = warehouse_service or WarehouseService()
        self.order_service = order_service or OrderDBService()
        self.llm_arbitrator = llm_arbitrator or LLMArbitrator()
        self.pdf_generator = pdf_generator or PDFGenerator()
        self.paypal_client = paypal_client or PayPalClient()

        # Thread-safe in-memory dispute registry: dispute_id -> DisputeRecord
        self._dispute_store: dict[str, DisputeRecord] = {}
        self._lock = asyncio.Lock()

    def get_record(self, dispute_id: str) -> DisputeRecord | None:
        """Retrieve stored dispute record."""
        return self._dispute_store.get(dispute_id)

    def list_records(
        self, stage: str | None = None, status: str | None = None
    ) -> list[DisputeRecord]:
        """List all dispute records matching optional filters."""
        records = list(self._dispute_store.values())
        if stage:
            records = [r for r in records if r.stage.value.upper() == stage.upper()]
        if status:
            records = [r for r in records if r.pipeline_status.value.upper() == status.upper()]
        return records

    def get_hitl_queue(self) -> list[DisputeRecord]:
        """List all disputes pending Human-in-the-Loop review."""
        return [
            r
            for r in self._dispute_store.values()
            if r.hitl_flagged and r.pipeline_status == PipelineExecutionStatus.FLAGGED_HITL
        ]

    async def process_webhook_event(
        self,
        event: PayPalWebhookEvent,
        correlation_id: str | None = None,
    ) -> DisputeRecord:
        """
        Main entrypoint: Processes incoming PayPal webhook event.
        Ensures idempotent handling and routes based on event type.
        """
        corr_id = correlation_id or f"CORR-{event.id}"
        dispute = event.resource
        dispute_id = dispute.dispute_id

        logger.info(f"[{corr_id}] Ingesting webhook {event.event_type} for dispute {dispute_id}.")

        # Handle RESOLVED events
        if event.event_type == "CUSTOMER.DISPUTE.RESOLVED":
            async with self._lock:
                existing = self._dispute_store.get(dispute_id)
                if existing:
                    existing.pipeline_status = PipelineExecutionStatus.RESOLVED
                    existing.audit_trail.append(
                        f"Dispute resolved externally by PayPal at {datetime.now(UTC).isoformat()}."
                    )
                    existing.updated_at = datetime.now(UTC)
                    return existing

        # Check idempotency for creation/processing
        async with self._lock:
            existing = self._dispute_store.get(dispute_id)
            if existing and existing.pipeline_status in (
                PipelineExecutionStatus.DEFENDED,
                PipelineExecutionStatus.CONCEDED,
                PipelineExecutionStatus.DE_ESCALATED,
                PipelineExecutionStatus.FLAGGED_HITL,
            ):
                logger.warning(
                    f"[{corr_id}] Dispute {dispute_id} already processed (Status: {existing.pipeline_status})."
                )
                return existing

        # Execute dispute analysis & dispatch pipeline
        return await self.execute_dispute_resolution(dispute=dispute, correlation_id=corr_id)

    async def execute_dispute_resolution(
        self,
        dispute: PayPalDisputeResource,
        correlation_id: str,
    ) -> DisputeRecord:
        """
        Gathers telemetry, runs arbitration, compiles evidence if needed, and executes PayPal actions.
        """
        dispute_id = dispute.dispute_id
        amount = dispute.dispute_amount.float_value

        # Extract transaction identifiers
        txn_id = None
        order_id = None
        customer_email = None
        if dispute.disputed_transactions:
            txn = dispute.disputed_transactions[0]
            txn_id = txn.seller_transaction_id or txn.buyer_transaction_id
            order_id = txn.invoice_number or txn.custom
            if txn.buyer:
                customer_email = txn.buyer.email

        # 1. Parallel Telemetry Gathering
        logger.info(f"[{correlation_id}] Fetching external telemetry for {dispute_id}...")
        try:
            carrier_task = self.carrier_service.get_tracking(
                tracking_number=None, order_id=order_id or dispute_id
            )
            wh_task = self.warehouse_service.get_fulfillment_telemetry(
                order_id=order_id or dispute_id
            )
            order_task = self.order_service.get_order_by_transaction_or_id(
                transaction_id=txn_id,
                order_id=order_id or dispute_id,
                disputed_amount=amount,
            )

            carrier_data, wh_data, order_data = await asyncio.gather(
                carrier_task, wh_task, order_task
            )
        except Exception as exc:
            logger.error(f"[{correlation_id}] Failed gathering telemetry: {exc}")
            record = DisputeRecord(
                dispute_id=dispute_id,
                stage=dispute.dispute_stage,
                reason=dispute.dispute_reason,
                amount=amount,
                pipeline_status=PipelineExecutionStatus.FAILED,
                audit_trail=[f"Telemetry gathering failed: {exc}"],
            )
            async with self._lock:
                self._dispute_store[dispute_id] = record
            return record

        # 2. Determine Dispute Fee
        fee = self.order_service.determine_dispute_fee(order_data.merchant_monthly_disputes_count)

        # 3. AI Arbitration Layer
        logger.info(f"[{correlation_id}] Executing AI arbitration for {dispute_id}...")
        decision: ArbitrationDecision = await self.llm_arbitrator.arbitrate(
            dispute=dispute,
            carrier=carrier_data,
            warehouse=wh_data,
            order=order_data,
            dispute_fee=fee,
        )

        # 4. Action Dispatching
        pipeline_status = PipelineExecutionStatus.ANALYZING
        action_taken = None
        api_response = None
        pdf_path = None

        if decision.hitl_flagged:
            pipeline_status = PipelineExecutionStatus.FLAGGED_HITL
            action_taken = "FLAGGED_FOR_HITL_REVIEW"
            logger.info(
                f"[{correlation_id}] Dispute {dispute_id} routed to HITL queue. Reasons: {decision.hitl_reasons}"
            )

        elif dispute.dispute_stage == DisputeStage.INQUIRY:
            if decision.recommended_action == ArbitrationAction.MAKE_OFFER:
                offer_amt = decision.offer_amount or round(amount * 0.50, 2)
                api_response = await self.paypal_client.make_offer(
                    dispute_id=dispute_id,
                    offer_amount=offer_amt,
                    note=decision.customer_message or "Settlement offer",
                    correlation_id=correlation_id,
                )
                action_taken = f"MADE_OFFER_${offer_amt:.2f}"
                pipeline_status = PipelineExecutionStatus.DE_ESCALATED
            else:
                msg = (
                    decision.customer_message
                    or "Thank you for reaching out. We are reviewing your order."
                )
                api_response = await self.paypal_client.send_message(
                    dispute_id=dispute_id,
                    message=msg,
                    correlation_id=correlation_id,
                )
                action_taken = "SENT_DE_ESCALATION_MESSAGE"
                pipeline_status = PipelineExecutionStatus.DE_ESCALATED

        elif dispute.dispute_stage in (
            DisputeStage.CLAIM,
            DisputeStage.PRE_ARBITRATION,
            DisputeStage.ARBITRATION,
        ):
            if decision.recommended_action == ArbitrationAction.PROVIDE_EVIDENCE:
                # Compile PDF evidentiary dossier
                pdf_bytes = self.pdf_generator.generate_rebuttal_dossier(
                    dispute=dispute,
                    decision=decision,
                    carrier=carrier_data,
                    warehouse=wh_data,
                    order=order_data,
                )
                pdf_path = f"artifacts/dossiers/dispute_{dispute_id}_evidence.pdf"

                # Dispatch evidence to PayPal
                api_response = await self.paypal_client.provide_evidence(
                    dispute_id=dispute_id,
                    pdf_bytes=pdf_bytes,
                    notes=decision.rebuttal_statement[:2000],  # PayPal character limit friendly
                    correlation_id=correlation_id,
                )
                action_taken = "PROVIDED_EVIDENCE_DOSSIER"
                pipeline_status = PipelineExecutionStatus.DEFENDED
            else:
                # Concede claim
                api_response = await self.paypal_client.accept_claim(
                    dispute_id=dispute_id,
                    note="Merchant concedes claim upon review.",
                    correlation_id=correlation_id,
                )
                action_taken = "ACCEPTED_CLAIM_CONCESSION"
                pipeline_status = PipelineExecutionStatus.CONCEDED

        # 5. Build and Store Record
        record = DisputeRecord(
            dispute_id=dispute_id,
            stage=dispute.dispute_stage,
            reason=dispute.dispute_reason,
            amount=amount,
            currency="USD",
            seller_transaction_id=txn_id,
            order_id=order_data.order_id,
            customer_email=customer_email or order_data.customer_email,
            pipeline_status=pipeline_status,
            win_probability=decision.win_probability,
            expected_value=decision.expected_value,
            dispute_fee_applied=decision.dispute_fee_applied,
            recommended_action=decision.recommended_action.value,
            action_taken=action_taken,
            hitl_flagged=decision.hitl_flagged,
            hitl_reasons=decision.hitl_reasons,
            rebuttal_statement=decision.rebuttal_statement,
            pdf_dossier_path=pdf_path,
            paypal_api_response=api_response,
            telemetry_carrier=carrier_data,
            telemetry_warehouse=wh_data,
            telemetry_order=order_data,
            audit_trail=[
                f"Ingested via webhook at {datetime.now(UTC).isoformat()}.",
                f"Telemetry assembled (Carrier: {carrier_data.status}, WH: {'OK' if wh_data.quality_inspection_passed else 'FAIL'}).",
                f"Arbitrated P(win)={decision.win_probability:.2f}, EV=${decision.expected_value:.2f}.",
                f"Action executed: {action_taken}.",
            ],
        )

        async with self._lock:
            self._dispute_store[dispute_id] = record

        logger.info(
            f"[{correlation_id}] Dispute {dispute_id} complete -> Status: {pipeline_status}."
        )
        return record

    async def override_hitl(
        self,
        dispute_id: str,
        override_req: HITLOverrideRequest,
    ) -> DisputeRecord:
        """
        Allows human reviewers to inspect, approve, or override a flagged dispute.
        Dispatches the chosen PayPal action immediately upon sign-off.
        """
        async with self._lock:
            record = self._dispute_store.get(dispute_id)
            if not record:
                raise DisputeNotFoundError(f"Dispute {dispute_id} not found.")

        logger.info(
            f"Applying HITL override on {dispute_id} by {override_req.reviewer_id}: {override_req.action}."
        )
        chosen_action = override_req.action.upper()
        api_response = None
        action_taken = None
        status = PipelineExecutionStatus.OVERRIDDEN

        if chosen_action == "DEFEND":
            # Generate dossier and provide evidence
            if record.telemetry_carrier and record.telemetry_warehouse and record.telemetry_order:
                # Reconstruct dispute resource
                dispute_res = PayPalDisputeResource(
                    dispute_id=record.dispute_id,
                    create_time=datetime.now(UTC).isoformat(),
                    dispute_amount={"currency_code": "USD", "value": f"{record.amount:.2f}"},  # type: ignore[arg-type]
                    dispute_stage=record.stage,
                    dispute_reason=record.reason,
                )
                arb_dec = ArbitrationDecision(
                    dispute_id=record.dispute_id,
                    win_probability=record.win_probability or 0.70,
                    expected_value=record.expected_value or 0.0,
                    recommended_action=ArbitrationAction.PROVIDE_EVIDENCE,
                    executive_summary=f"Human override approved by {override_req.reviewer_id}.",
                    rebuttal_statement=record.rebuttal_statement
                    or "Evidence provided following manual review.",
                )
                pdf_bytes = self.pdf_generator.generate_rebuttal_dossier(
                    dispute=dispute_res,
                    decision=arb_dec,
                    carrier=record.telemetry_carrier,
                    warehouse=record.telemetry_warehouse,
                    order=record.telemetry_order,
                )
                record.pdf_dossier_path = f"artifacts/dossiers/dispute_{dispute_id}_evidence.pdf"
                api_response = await self.paypal_client.provide_evidence(
                    dispute_id=dispute_id,
                    pdf_bytes=pdf_bytes,
                    notes=override_req.override_reason,
                )
                action_taken = "HUMAN_OVERRIDE_DEFENDED"
                status = PipelineExecutionStatus.DEFENDED

        elif chosen_action == "CONCEDE":
            api_response = await self.paypal_client.accept_claim(
                dispute_id=dispute_id,
                note=f"Conceded following review by {override_req.reviewer_id}: {override_req.override_reason}",
            )
            action_taken = "HUMAN_OVERRIDE_CONCEDED"
            status = PipelineExecutionStatus.CONCEDED

        elif chosen_action == "SEND_MESSAGE":
            msg = (
                override_req.adjusted_message
                or "Thank you for your inquiry. Our support team is assisting you."
            )
            api_response = await self.paypal_client.send_message(dispute_id=dispute_id, message=msg)
            action_taken = "HUMAN_OVERRIDE_MESSAGE_SENT"
            status = PipelineExecutionStatus.DE_ESCALATED

        elif chosen_action == "MAKE_OFFER":
            amt = override_req.adjusted_offer_amount or round(record.amount * 0.50, 2)
            api_response = await self.paypal_client.make_offer(
                dispute_id=dispute_id,
                offer_amount=amt,
                note=override_req.override_reason,
            )
            action_taken = f"HUMAN_OVERRIDE_MADE_OFFER_${amt:.2f}"
            status = PipelineExecutionStatus.DE_ESCALATED

        async with self._lock:
            record.pipeline_status = status
            record.action_taken = action_taken
            record.hitl_reviewed_by = override_req.reviewer_id
            record.hitl_override_action = chosen_action
            record.paypal_api_response = api_response
            record.audit_trail.append(
                f"HITL Override applied by {override_req.reviewer_id} at {datetime.now(UTC).isoformat()}: "
                f"Action={chosen_action}, Reason='{override_req.override_reason}'."
            )
            record.updated_at = datetime.now(UTC)

        return record

    def get_stats_summary(self) -> DisputeStatsSummary:
        """Calculate executive metrics across all ingested disputes."""
        records = list(self._dispute_store.values())
        total = len(records)
        defended = sum(1 for r in records if r.pipeline_status == PipelineExecutionStatus.DEFENDED)
        conceded = sum(1 for r in records if r.pipeline_status == PipelineExecutionStatus.CONCEDED)
        de_esc = sum(
            1 for r in records if r.pipeline_status == PipelineExecutionStatus.DE_ESCALATED
        )
        hitl = sum(1 for r in records if r.pipeline_status == PipelineExecutionStatus.FLAGGED_HITL)
        tot_amount = sum(r.amount for r in records)
        tot_ev = sum(r.expected_value or 0.0 for r in records)
        # Avoided fees: each defended claim won or conceded claim avoiding $15/$30 escalation
        fees_avoided = sum(
            r.dispute_fee_applied or 15.0
            for r in records
            if r.pipeline_status
            in (PipelineExecutionStatus.DEFENDED, PipelineExecutionStatus.CONCEDED)
        )
        avg_p = (sum(r.win_probability or 0.0 for r in records) / total) if total > 0 else 0.0

        return DisputeStatsSummary(
            total_disputes=total,
            defended_count=defended,
            conceded_count=conceded,
            de_escalated_count=de_esc,
            hitl_queue_count=hitl,
            total_disputed_amount=round(tot_amount, 2),
            total_expected_value=round(tot_ev, 2),
            estimated_dispute_fees_avoided=round(fees_avoided, 2),
            average_win_probability=round(avg_p, 3),
        )


# Global singleton instance for the application
pipeline_instance = DisputePipeline()


def get_dispute_pipeline() -> DisputePipeline:
    """Dependency provider for DisputePipeline."""
    return pipeline_instance
