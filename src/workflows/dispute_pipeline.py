"""
Dispute Pipeline Orchestrator: Chaining Ingestion -> Telemetry -> Compliance -> CE 3.0 -> AI -> Dispatch.
Enterprise-grade lifecycle management with multi-tenant isolation, conversational bots, and ERP accounting.
"""

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from src.core.config import get_settings
from src.core.exceptions import DisputeNotFoundError
from src.core.tenant import TenantManager, get_tenant_manager
from src.models.arbitration import ArbitrationAction, ArbitrationDecision
from src.models.schemas import (
    BillingTelemetryInfo,
    BuyerInfo,
    CarrierTrackingInfo,
    DisputeMessage,
    DisputeReason,
    DisputeRecord,
    DisputeStage,
    DisputeStatsSummary,
    DisputeStatus,
    DisputedTransaction,
    HITLOverrideRequest,
    Money,
    OrderCustomerInfo,
    PayPalDisputeMessage,
    PayPalDisputeResource,
    PayPalWebhookEvent,
    PipelineExecutionStatus,
    WarehouseFulfillmentInfo,
    normalize_dispute_reason,
)
from src.services.accounting import AccountingIntegrationService
from src.services.billing import BillingTelemetryService
from src.services.buyer_simulator import first_buyer_message, next_buyer_message
from src.services.carrier import CarrierService
from src.services.compliance import ComplianceAuditResult, SellerProtectionComplianceEngine
from src.services.conversation_bot import ConversationalSettlementBot, NegotiationStep
from src.services.llm_arbitrator import LLMArbitrator
from src.services.llm_orchestrator import MultiModelLLMOrchestrator, OrchestrationTier
from src.services.order import OrderDBService
from src.services.paypal_client import PayPalClient
from src.services.pdf_generator import PDFGenerator
from src.services.rma import RMAManager
from src.services.visa_ce3 import CE3QualificationResult, VisaCompellingEvidenceEngine
from src.services.warehouse import WarehouseService

logger = logging.getLogger(__name__)

CANONICAL_DEMO_SPECS: dict[str, dict[str, Any]] = {
    "PP-D-99412": {
        "order_id": "ORD-ZAP-99412",
        "txn_id": "TXN-ZAP-99412",
        "buyer_name": "Elena Rostova",
        "buyer_email": "elena.rostova@example.com",
        "amount": 349.00,
        "currency": "USD",
        "reason": DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED,
        "stage": DisputeStage.CLAIM,
    },
    "PP-D-77194": {
        "order_id": "ORD-ZAP-77194",
        "txn_id": "TXN-ZAP-77194",
        "buyer_name": "Samantha Cole",
        "buyer_email": "samantha.cole@outlook.com",
        "amount": 299.99,
        "currency": "USD",
        "reason": DisputeReason.UNAUTHORISED,
        "stage": DisputeStage.CLAIM,
    },
    "PP-D-55210": {
        "order_id": "ORD-ZAP-55210",
        "txn_id": "TXN-ZAP-55210",
        "buyer_name": "Sophia Chen",
        "buyer_email": "sophia.chen@enterprise.io",
        "amount": 79.00,
        "currency": "USD",
        "reason": DisputeReason.CANCELED_RECURRING_BILLING,
        "stage": DisputeStage.INQUIRY,
    },
    "PP-D-44102": {
        "order_id": "ORD-ZAP-44102",
        "txn_id": "TXN-ZAP-44102",
        "buyer_name": "Liam Smith",
        "buyer_email": "liam.smith@example.com",
        "amount": 35.00,
        "currency": "USD",
        "reason": DisputeReason.CREDIT_NOT_PROCESSED,
        "stage": DisputeStage.CLAIM,
    },
    "PP-D-66305": {
        "order_id": "ORD-ZAP-66305",
        "txn_id": "TXN-ZAP-66305",
        "buyer_name": "Jordan Lee",
        "buyer_email": "jordan.lee@techcorp.io",
        "amount": 849.00,
        "currency": "USD",
        "reason": DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        "stage": DisputeStage.CLAIM,
    },
    "PP-D-88201": {
        "order_id": "ORD-ZAP-10294",
        "txn_id": "TXN-ZAP-10294",
        "buyer_name": "Marcus Vance",
        "buyer_email": "marcus.vance@gmail.com",
        "amount": 249.99,
        "currency": "USD",
        "reason": DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        "stage": DisputeStage.INQUIRY,
    },
}


class DisputePipeline:
    """Enterprise orchestrator for automated dispute intake, compliance guardrails, and resolution."""

    def __init__(
        self,
        carrier_service: CarrierService | None = None,
        warehouse_service: WarehouseService | None = None,
        order_service: OrderDBService | None = None,
        billing_service: BillingTelemetryService | None = None,
        llm_arbitrator: LLMArbitrator | None = None,
        pdf_generator: PDFGenerator | None = None,
        paypal_client: PayPalClient | None = None,
        compliance_engine: SellerProtectionComplianceEngine | None = None,
        visa_ce3_engine: VisaCompellingEvidenceEngine | None = None,
        conversation_bot: ConversationalSettlementBot | None = None,
        accounting_service: AccountingIntegrationService | None = None,
        rma_manager: RMAManager | None = None,
        tenant_manager: TenantManager | None = None,
        llm_orchestrator: MultiModelLLMOrchestrator | None = None,
    ) -> None:
        self.settings = get_settings()
        self.carrier_service = carrier_service or CarrierService()
        self.warehouse_service = warehouse_service or WarehouseService()
        self.order_service = order_service or OrderDBService()
        self.billing_service = billing_service or BillingTelemetryService()
        self.llm_arbitrator = llm_arbitrator or LLMArbitrator()
        self.pdf_generator = pdf_generator or PDFGenerator()
        self.paypal_client = paypal_client or PayPalClient()
        self.compliance_engine = compliance_engine or SellerProtectionComplianceEngine()
        self.visa_ce3_engine = visa_ce3_engine or VisaCompellingEvidenceEngine()
        self.conversation_bot = conversation_bot or ConversationalSettlementBot()
        self.accounting_service = accounting_service or AccountingIntegrationService()
        self.rma_manager = rma_manager or RMAManager()
        self.tenant_manager = tenant_manager or get_tenant_manager()
        # Used only for buyer conversation (merchant replies, simulated buyer), so the fast chat chain.
        self.llm_orchestrator = llm_orchestrator or MultiModelLLMOrchestrator(purpose="chat")

        # Thread-safe in-memory dispute registry: dispute_id -> DisputeRecord
        self._dispute_store: dict[str, DisputeRecord] = {}
        self._lock: asyncio.Lock | None = None

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def sync_from_db(self) -> None:
        """Loads all persistent dispute records from the database into the runtime registry using direct SQLite."""
        try:
            import json
            import sqlite3

            from src.core.config import get_sqlite_db_path

            conn = sqlite3.connect(get_sqlite_db_path(), timeout=5.0)
            c = conn.cursor()
            rows = c.execute("""
                SELECT dispute_id, merchant_id, stage, reason, amount, currency,
                       seller_transaction_id, order_id, customer_email, pipeline_status,
                       win_probability, expected_value, dispute_fee_applied, action_taken,
                       hitl_flagged, hitl_reasons, rebuttal_statement, pdf_dossier_path,
                       paypal_api_response, compliance_eligible, compliance_disqualifications,
                       visa_ce3_qualified, rma_number, telemetry_carrier, telemetry_warehouse,
                       audit_trail, created_at, updated_at, recommended_action,
                       hitl_reviewed_by, hitl_override_action, pdf_dossier_sha256,
                       specialist_agent, persona_mode, llm_tier_used, seller_rights_met,
                       reasoning_steps, telemetry_order, telemetry_billing, messages
                FROM disputes
            """).fetchall()
            conn.close()

            self._dispute_store.clear()
            for r in rows:
                c_data = json.loads(r[23]) if r[23] else None
                w_data = json.loads(r[24]) if r[24] else None
                o_data = json.loads(r[37]) if r[37] else None
                b_data = json.loads(r[38]) if r[38] else None
                self._dispute_store[r[0]] = DisputeRecord(
                    dispute_id=r[0],
                    merchant_id=r[1],
                    stage=DisputeStage(r[2]),
                    reason=normalize_dispute_reason(r[3]),
                    amount=r[4],
                    currency=r[5],
                    seller_transaction_id=r[6],
                    order_id=r[7],
                    customer_email=r[8],
                    pipeline_status=PipelineExecutionStatus(r[9]),
                    win_probability=r[10],
                    expected_value=r[11],
                    dispute_fee_applied=r[12],
                    recommended_action=r[28],
                    action_taken=r[13],
                    hitl_flagged=bool(r[14]),
                    hitl_reasons=json.loads(r[15]) if r[15] else [],
                    hitl_reviewed_by=r[29],
                    hitl_override_action=r[30],
                    rebuttal_statement=r[16],
                    pdf_dossier_path=r[17],
                    pdf_dossier_sha256=r[31],
                    paypal_api_response=json.loads(r[18]) if r[18] else None,
                    compliance_eligible=bool(r[19]),
                    compliance_disqualifications=json.loads(r[20]) if r[20] else [],
                    visa_ce3_qualified=bool(r[21]),
                    rma_number=r[22],
                    specialist_agent=r[32],
                    persona_mode=r[33],
                    llm_tier_used=r[34],
                    seller_rights_met=bool(r[35]) if r[35] is not None else None,
                    reasoning_steps=json.loads(r[36]) if r[36] else [],
                    telemetry_carrier=(
                        CarrierTrackingInfo(
                            tracking_number=c_data.get("tracking_number", "UNKNOWN"),
                            carrier_name=c_data.get("carrier_name", "FedEx"),
                            status=c_data.get("status", "DELIVERED"),
                            ship_date=c_data.get("ship_date", "2026-10-15T09:00:00Z"),
                            destination_address=c_data.get(
                                "destination_address", "Confirmed Address"
                            ),
                            delivered_date=c_data.get("delivered_date"),
                            signed_by=c_data.get("signed_by"),
                            gps_latitude=c_data.get("gps_latitude"),
                            gps_longitude=c_data.get("gps_longitude"),
                        )
                        if c_data
                        else None
                    ),
                    telemetry_warehouse=(
                        WarehouseFulfillmentInfo(
                            order_id=r[7] or r[0],
                            pack_timestamp=w_data.get("pack_timestamp", "2026-10-15T08:30:00Z"),
                            warehouse_id=w_data.get("warehouse_id", "WH-01"),
                            packer_id=w_data.get("packer_id", "PACKER-01"),
                            scale_measured_weight_kg=w_data.get("scale_measured_weight_kg", 1.40),
                            expected_weight_kg=w_data.get("expected_weight_kg", 1.40),
                            weight_delta_percent=w_data.get("weight_delta_percent", 0.0),
                            scanned_serials=w_data.get("scanned_serials", []),
                            tamper_seal_id=w_data.get("tamper_seal_id", "SEAL-001"),
                            packing_station_photo_url=w_data.get(
                                "packing_station_photo_url", "artifacts/wh.jpg"
                            ),
                            quality_inspection_passed=w_data.get("quality_inspection_passed", True),
                        )
                        if w_data
                        else None
                    ),
                    telemetry_order=OrderCustomerInfo(**o_data) if o_data else None,
                    telemetry_billing=BillingTelemetryInfo(**b_data) if b_data else None,
                    audit_trail=json.loads(r[25]) if r[25] else [],
                    messages=[DisputeMessage(**m) for m in json.loads(r[39])] if r[39] else [],
                )
            if rows:
                logger.info(f"Synchronized {len(rows)} disputes from database.")
            else:
                await self.seed_canonical_disputes()
        except Exception as exc:
            logger.warning(f"Dispute database sync notice: {exc}")

    async def _save_record_to_db(self, record: DisputeRecord) -> None:
        """Persists or updates a dispute record in the database using direct SQLite."""
        try:
            import json
            import sqlite3

            from src.core.config import get_sqlite_db_path

            conn = sqlite3.connect(get_sqlite_db_path(), timeout=5.0)
            c = conn.cursor()
            c.execute(
                """
                INSERT OR REPLACE INTO disputes (
                    dispute_id, merchant_id, stage, reason, amount, currency,
                    seller_transaction_id, order_id, customer_email, pipeline_status,
                    recommended_action, action_taken, hitl_flagged, hitl_reasons,
                    hitl_reviewed_by, hitl_override_action, rebuttal_statement,
                    pdf_dossier_path, pdf_dossier_sha256, paypal_api_response,
                    specialist_agent, persona_mode, llm_tier_used, seller_rights_met,
                    reasoning_steps, compliance_eligible, compliance_disqualifications,
                    visa_ce3_qualified, rma_number, telemetry_carrier,
                    telemetry_warehouse, telemetry_order, telemetry_billing, audit_trail,
                    win_probability, expected_value, dispute_fee_applied, created_at, updated_at,
                    messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.dispute_id,
                    record.merchant_id,
                    record.stage.value,
                    record.reason.value,
                    record.amount,
                    record.currency,
                    record.seller_transaction_id,
                    record.order_id,
                    record.customer_email,
                    record.pipeline_status.value,
                    record.recommended_action,
                    record.action_taken,
                    1 if record.hitl_flagged else 0,
                    json.dumps(record.hitl_reasons),
                    record.hitl_reviewed_by,
                    record.hitl_override_action,
                    record.rebuttal_statement,
                    record.pdf_dossier_path,
                    record.pdf_dossier_sha256,
                    json.dumps(record.paypal_api_response) if record.paypal_api_response else None,
                    record.specialist_agent,
                    record.persona_mode,
                    record.llm_tier_used,
                    None
                    if record.seller_rights_met is None
                    else (1 if record.seller_rights_met else 0),
                    json.dumps(record.reasoning_steps),
                    1 if (record.compliance_eligible is None or record.compliance_eligible) else 0,
                    json.dumps(record.compliance_disqualifications),
                    1 if record.visa_ce3_qualified else 0,
                    record.rma_number,
                    (
                        json.dumps(record.telemetry_carrier.model_dump())
                        if record.telemetry_carrier
                        else None
                    ),
                    (
                        json.dumps(record.telemetry_warehouse.model_dump())
                        if record.telemetry_warehouse
                        else None
                    ),
                    (
                        json.dumps(record.telemetry_order.model_dump())
                        if record.telemetry_order
                        else None
                    ),
                    (
                        json.dumps(record.telemetry_billing.model_dump())
                        if record.telemetry_billing
                        else None
                    ),
                    json.dumps(record.audit_trail),
                    record.win_probability,
                    record.expected_value,
                    record.dispute_fee_applied or 15.0,
                    (
                        record.created_at.isoformat()
                        if hasattr(record.created_at, "isoformat")
                        else str(record.created_at)
                    ),
                    (
                        record.updated_at.isoformat()
                        if hasattr(record.updated_at, "isoformat")
                        else str(record.updated_at)
                    ),
                    json.dumps([m.model_dump() for m in record.messages]),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning(f"Could not persist dispute {record.dispute_id} to database: {exc}")

    async def ensure_demo_dispute(self, dispute_id: str) -> DisputeRecord | None:
        """Dynamically synthesizes and compiles PDF dossier on-demand for canonical demo disputes."""
        spec = CANONICAL_DEMO_SPECS.get(dispute_id)
        if not spec:
            return None

        async with self.lock:
            existing = self._dispute_store.get(dispute_id)
            if existing and existing.pdf_dossier_path and os.path.exists(existing.pdf_dossier_path):
                return existing

        dispute = PayPalDisputeResource(
            dispute_id=dispute_id,
            create_time=datetime.now(UTC).isoformat(),
            disputed_transactions=[
                DisputedTransaction(
                    buyer_transaction_id=spec["txn_id"],
                    seller_transaction_id=spec["txn_id"],
                    gross_amount=Money(currency_code=spec["currency"], value=f"{spec['amount']:.2f}"),
                    invoice_number=spec["order_id"],
                    custom=spec["order_id"],
                    buyer=BuyerInfo(name=spec["buyer_name"], email=spec["buyer_email"]),
                )
            ],
            dispute_amount=Money(currency_code=spec["currency"], value=f"{spec['amount']:.2f}"),
            dispute_stage=spec["stage"],
            dispute_reason=spec["reason"],
            status=DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
        )

        return await self.execute_dispute_resolution(
            dispute=dispute,
            correlation_id=f"CORR-CANONICAL-{dispute_id}",
            merchant_id="default-merchant",
        )

    async def seed_canonical_disputes(self) -> None:
        """Seed all canonical demo disputes on startup so the UI, radar, and dossiers are active immediately."""
        logger.info("Seeding canonical demo disputes into pipeline registry...")
        for dispute_id in CANONICAL_DEMO_SPECS:
            try:
                await self.ensure_demo_dispute(dispute_id)
            except Exception as exc:
                logger.warning(f"Could not seed canonical dispute {dispute_id}: {exc}")

    def get_record(self, dispute_id: str) -> DisputeRecord | None:
        """Retrieve stored dispute record."""
        return self._dispute_store.get(dispute_id)

    def list_records(
        self, stage: str | None = None, status: str | None = None, merchant_id: str | None = None
    ) -> list[DisputeRecord]:
        """List all dispute records matching optional filters."""
        records = list(self._dispute_store.values())
        if merchant_id:
            records = [r for r in records if r.merchant_id == merchant_id]
        if stage:
            records = [r for r in records if r.stage.value.upper() == stage.upper()]
        if status:
            records = [r for r in records if r.pipeline_status.value.upper() == status.upper()]
        return records

    def get_hitl_queue(self, merchant_id: str | None = None) -> list[DisputeRecord]:
        """List all disputes pending Human-in-the-Loop review."""
        records = [
            r
            for r in self._dispute_store.values()
            if r.hitl_flagged and r.pipeline_status == PipelineExecutionStatus.FLAGGED_HITL
        ]
        if merchant_id:
            records = [r for r in records if r.merchant_id == merchant_id]
        return records

    async def process_webhook_event(
        self,
        event: PayPalWebhookEvent,
        correlation_id: str | None = None,
        merchant_id: str | None = None,
    ) -> DisputeRecord:
        """
        Main intake entrypoint: Processes incoming PayPal webhook event with idempotency.
        """
        corr_id = correlation_id or f"CORR-{event.id}"
        dispute = event.resource
        dispute_id = dispute.dispute_id
        effective_merchant = merchant_id or "default-merchant"

        logger.info(
            f"[{corr_id}] Ingesting webhook {event.event_type} for dispute {dispute_id} (Merchant: {effective_merchant})."
        )

        # Handle external dispute resolution events
        if event.event_type == "CUSTOMER.DISPUTE.RESOLVED":
            async with self.lock:
                existing = self._dispute_store.get(dispute_id)
                if existing:
                    existing.pipeline_status = PipelineExecutionStatus.RESOLVED
                    existing.audit_trail.append(
                        f"Dispute resolved externally by PayPal at {datetime.now(UTC).isoformat()}."
                    )
                    existing.updated_at = datetime.now(UTC)
                    return existing

        # Buyer replies and other changes to a dispute we already hold. Without this branch the
        # idempotency check below would drop the update as "already processed".
        if event.event_type == "CUSTOMER.DISPUTE.UPDATED":
            existing = self._dispute_store.get(dispute_id)
            if existing:
                return await self.handle_dispute_update(existing, dispute, corr_id)

        # Idempotency check
        async with self.lock:
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

        return await self.execute_dispute_resolution(
            dispute=dispute,
            correlation_id=corr_id,
            merchant_id=effective_merchant,
        )

    async def handle_dispute_update(
        self,
        record: DisputeRecord,
        dispute: PayPalDisputeResource,
        correlation_id: str,
    ) -> DisputeRecord:
        """
        Handles CUSTOMER.DISPUTE.UPDATED for a dispute already in the registry.

        PayPal resends the whole message thread on every update, so only messages not already
        stored are added. When the buyer has written something new, an AI-drafted reply is sent
        back through PayPal, unless the dispute is awaiting human review or already closed.
        """
        now = datetime.now(UTC).isoformat()

        async with self.lock:
            # Buyer messages keep PayPal's timestamp; our own replies come back from PayPal with a
            # different timestamp, so seller/arbiter messages are matched on content alone.
            def message_key(sender: str, timestamp: str, content: str) -> tuple[str, ...]:
                return (sender, timestamp, content) if sender == "BUYER" else (sender, content)

            known = {message_key(m.sender, m.timestamp, m.content) for m in record.messages}
            new_messages: list[DisputeMessage] = []
            for msg in dispute.messages:
                content = (msg.content or "").strip()
                if not content:
                    continue
                entry = DisputeMessage(
                    sender=msg.posted_by.upper(),
                    content=content,
                    timestamp=msg.time_posted or now,
                )
                key = message_key(entry.sender, entry.timestamp, entry.content)
                if key not in known:
                    known.add(key)
                    new_messages.append(entry)
            record.messages.extend(new_messages)
            new_buyer_messages = [m for m in new_messages if m.sender == "BUYER"]

            if dispute.dispute_stage != record.stage:
                record.audit_trail.append(
                    f"PayPal moved the dispute from {record.stage.value} to {dispute.dispute_stage.value} at {now}."
                )
                record.stage = dispute.dispute_stage
            record.audit_trail.append(
                f"Dispute update received at {now}: {len(new_buyer_messages)} new buyer message(s)."
            )
            record.updated_at = datetime.now(UTC)
            status = record.pipeline_status

        if not new_buyer_messages:
            await self._save_record_to_db(record)
            return record

        if status == PipelineExecutionStatus.FLAGGED_HITL:
            skip_reason = "the dispute is awaiting human review"
        elif status in (PipelineExecutionStatus.RESOLVED, PipelineExecutionStatus.CONCEDED):
            skip_reason = "the dispute is already closed"
        else:
            skip_reason = None

        if skip_reason:
            async with self.lock:
                record.audit_trail.append(f"No automatic reply sent because {skip_reason}.")
            await self._save_record_to_db(record)
            return record

        reply_text, tier_used = await self._draft_buyer_reply(
            record, new_buyer_messages[-1].content
        )
        try:
            api_response = await self.paypal_client.send_message(
                dispute_id=record.dispute_id,
                message=reply_text,
                correlation_id=correlation_id,
            )
        except Exception as exc:
            logger.error(f"[{correlation_id}] Failed to send reply for {record.dispute_id}: {exc}")
            async with self.lock:
                record.audit_trail.append(f"Reply to buyer could not be sent: {exc}")
            await self._save_record_to_db(record)
            return record

        is_ai = tier_used != OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC.value
        async with self.lock:
            record.messages.append(
                DisputeMessage(
                    sender="SELLER",
                    content=reply_text,
                    timestamp=datetime.now(UTC).isoformat(),
                    source="AI_REPLY" if is_ai else "TEMPLATE_REPLY",
                    llm_tier_used=tier_used,
                )
            )
            record.paypal_api_response = api_response
            record.audit_trail.append(
                f"Replied to the buyer via PayPal send-message ({'AI' if is_ai else 'template'}: {tier_used})."
            )
            record.updated_at = datetime.now(UTC)
        await self._save_record_to_db(record)
        return record

    @staticmethod
    def _opening_messages(
        outreach_message: str | None, decision: ArbitrationDecision
    ) -> list[DisputeMessage]:
        """The merchant's first message to the buyer, so the stored thread starts where PayPal's does."""
        if not outreach_message:
            return []
        written_by_ai = (
            outreach_message == decision.customer_message
            and decision.llm_tier_used != OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC.value
        )
        return [
            DisputeMessage(
                sender="SELLER",
                content=outreach_message,
                timestamp=datetime.now(UTC).isoformat(),
                source="AI_REPLY" if written_by_ai else "TEMPLATE_REPLY",
                llm_tier_used=decision.llm_tier_used,
            )
        ]

    async def simulate_buyer_turn(
        self, dispute_id: str, message: str | None = None
    ) -> DisputeRecord:
        """
        Demo: the buyer sends one message, then the merchant's AI reply follows.

        Without `message`, the buyer's first message is a template for the dispute reason and later
        ones are written by the LLM playing the buyer. The message is delivered as a
        CUSTOMER.DISPUTE.UPDATED event, exactly as a real PayPal webhook would deliver it.
        """
        record = self._dispute_store.get(dispute_id)
        if not record:
            raise DisputeNotFoundError(f"Dispute '{dispute_id}' not found in registry.")

        tier_used: str | None = None
        if message:
            source = "SIMULATED_MANUAL"
        elif not any(m.sender == "BUYER" for m in record.messages):
            message, source = first_buyer_message(record), "SIMULATED_TEMPLATE"
        else:
            message, tier_used = await next_buyer_message(record, self.llm_orchestrator)
            is_ai = tier_used != OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC.value
            source = "SIMULATED_AI" if is_ai else "SIMULATED_TEMPLATE"

        now = datetime.now(UTC).isoformat()
        # PayPal sends the whole thread on each update, so include what we already hold.
        thread = [
            PayPalDisputeMessage(posted_by=m.sender, time_posted=m.timestamp, content=m.content)
            for m in record.messages
        ]
        thread.append(PayPalDisputeMessage(posted_by="BUYER", time_posted=now, content=message))
        event = PayPalWebhookEvent(
            id=f"WH-EVT-{uuid.uuid4().hex[:12].upper()}",
            event_version="1.0",
            create_time=now,
            resource_type="dispute",
            event_type="CUSTOMER.DISPUTE.UPDATED",
            summary=f"Simulated buyer message on {dispute_id}",
            resource=PayPalDisputeResource(
                dispute_id=dispute_id,
                create_time=record.created_at.isoformat(),
                update_time=now,
                dispute_amount=Money(currency_code=record.currency, value=f"{record.amount:.2f}"),
                dispute_stage=record.stage,
                dispute_reason=record.reason,
                messages=thread,
            ),
        )
        record = await self.process_webhook_event(
            event=event,
            correlation_id=f"CORR-SIM-MSG-{uuid.uuid4().hex[:8].upper()}",
            merchant_id=record.merchant_id,
        )

        # Label the simulated buyer message so the dashboard can show how it was written.
        async with self.lock:
            for stored in reversed(record.messages):
                if stored.sender == "BUYER" and stored.content == message:
                    stored.source = source
                    stored.llm_tier_used = tier_used
                    break
        await self._save_record_to_db(record)
        return record

    async def send_seller_message(
        self, dispute_id: str, message: str, correlation_id: str | None = None
    ) -> DisputeRecord:
        """Sends a merchant-written message to the buyer via PayPal and stores it on the record."""
        record = self._dispute_store.get(dispute_id)
        if not record:
            raise DisputeNotFoundError(f"Dispute '{dispute_id}' not found in registry.")
        api_response = await self.paypal_client.send_message(
            dispute_id=dispute_id,
            message=message,
            correlation_id=correlation_id,
        )
        async with self.lock:
            record.messages.append(
                DisputeMessage(
                    sender="SELLER",
                    content=message,
                    timestamp=datetime.now(UTC).isoformat(),
                    source="DASHBOARD",
                )
            )
            record.paypal_api_response = api_response
            record.audit_trail.append("Merchant sent a message to the buyer from the dashboard.")
            record.updated_at = datetime.now(UTC)
        await self._save_record_to_db(record)
        return record

    async def _draft_buyer_reply(
        self, record: DisputeRecord, buyer_message: str
    ) -> tuple[str, str]:
        """Drafts a reply to the buyer with the LLM orchestrator; falls back to a safe template."""
        carrier = record.telemetry_carrier
        order = record.telemetry_order
        greeting = f"Hello {order.customer_name}," if order and order.customer_name else "Hello,"

        facts = [
            f"Dispute reason: {record.reason.value}",
            f"Stage: {record.stage.value}",
            f"Amount: {record.amount:.2f} {record.currency}",
        ]
        if order:
            facts.append(f"Order: {order.order_id}, buyer: {order.customer_name}")
        if carrier:
            delivery = f"Carrier: {carrier.carrier_name}, tracking {carrier.tracking_number}, status {carrier.status}"
            if carrier.delivered_date:
                delivery += f", delivered {carrier.delivered_date}"
            if carrier.signed_by:
                delivery += f", signed by {carrier.signed_by}"
            facts.append(delivery)
        history = "\n".join(f"{m.sender}: {m.content}" for m in record.messages[-8:])

        system_prompt = (
            "You write replies from an online merchant to a buyer inside a PayPal dispute. "
            "Be courteous, concise (under 120 words) and factual. Use only the facts provided. "
            "Never offer refunds, discounts, money or replacements, never admit fault, and never "
            "make promises about the dispute outcome. Answer the buyer's latest message, point to "
            "the relevant evidence, and ask a clarifying question when it helps. "
            "Move the conversation forward: do not repeat sentences from your earlier messages, and "
            "once the evidence has been shared, respond to what the buyer says instead of restating it. "
            "You are the merchant: when the buyer asks for something the merchant does (such as "
            "contacting the carrier), say what you will do next rather than asking the buyer about it. "
            "Write dates in plain English (for example 'October 24, 2026'), never as raw timestamps. "
            "Reply with JSON only."
        )
        user_prompt = (
            "Facts:\n- "
            + "\n- ".join(facts)
            + f"\n\nConversation so far:\n{history}"
            + f"\n\nLatest buyer message:\n{buyer_message}"
            + '\n\nReturn exactly: {"customer_message": "<reply to the buyer>", "reasoning_steps": ["<short step>"]}'
        )

        result = await self.llm_orchestrator.invoke_with_fallback(system_prompt, user_prompt)
        for reason in result.fallback_reasons:
            logger.warning(f"Buyer reply for {record.dispute_id}: {reason}")
        text = (result.payload.customer_message or "").strip() if result.payload else ""
        if text:
            return text, result.tier_used.value

        template = (
            f"{greeting} thank you for your message. We've received it and are reviewing your case"
        )
        if carrier:
            template += f", including the {carrier.carrier_name} tracking record for {carrier.tracking_number}"
        template += ". We'll follow up with you here shortly."
        return template, OrchestrationTier.TIER_3_DETERMINISTIC_HEURISTIC.value

    async def execute_dispute_resolution(
        self,
        dispute: PayPalDisputeResource,
        correlation_id: str,
        merchant_id: str = "default-merchant",
    ) -> DisputeRecord:
        """
        Executes end-to-end resolution:
        1. Tenant credentials & rules resolution
        2. ERP accounting ledger frozen funds logging
        3. Parallel logistics telemetry gathering
        4. PayPal Seller Protection compliance audit ($750 mandate, AVS check)
        5. Visa Compelling Evidence 3.0 pre-dispute matching
        6. AI arbitration & financial expected value calculation
        7. Conversational bot or formal defense dispatching
        """
        dispute_id = dispute.dispute_id
        amount = dispute.dispute_amount.float_value

        # Resolve tenant configuration
        tenant = self.tenant_manager.get_tenant(merchant_id)

        # Extract transaction identifiers
        txn_id = None
        order_id = None
        customer_email = None
        customer_name = None
        if dispute.disputed_transactions:
            txn = dispute.disputed_transactions[0]
            txn_id = txn.seller_transaction_id or txn.buyer_transaction_id
            order_id = txn.invoice_number or txn.custom
            if txn.buyer:
                customer_email = txn.buyer.email
                customer_name = txn.buyer.name

        effective_order_id = order_id or dispute_id

        # 1. Log ERP Accounting Frozen Funds Liability
        self.accounting_service.log_dispute_intake_frozen_funds(
            dispute_id=dispute_id,
            merchant_id=tenant.merchant_id,
            order_id=effective_order_id,
            amount=amount,
        )

        # 2. Parallel Telemetry Gathering
        logger.info(f"[{correlation_id}] Fetching external telemetry for {dispute_id}...")
        try:
            carrier_task = self.carrier_service.get_tracking(
                tracking_number=None,
                order_id=effective_order_id,
                customer_name=customer_name,
                customer_email=customer_email,
            )
            wh_task = self.warehouse_service.get_fulfillment_telemetry(order_id=effective_order_id)
            order_task = self.order_service.get_order_by_transaction_or_id(
                transaction_id=txn_id,
                order_id=effective_order_id,
                disputed_amount=amount,
                customer_name=customer_name,
                customer_email=customer_email,
            )
            billing_task = self.billing_service.get_billing_telemetry(order_id=effective_order_id)

            carrier_data, wh_data, order_data, billing_data = await asyncio.gather(
                carrier_task, wh_task, order_task, billing_task
            )
        except Exception as exc:
            logger.error(f"[{correlation_id}] Failed gathering telemetry: {exc}")
            record = DisputeRecord(
                dispute_id=dispute_id,
                merchant_id=tenant.merchant_id,
                stage=dispute.dispute_stage,
                reason=dispute.dispute_reason,
                amount=amount,
                pipeline_status=PipelineExecutionStatus.FAILED,
                audit_trail=[f"Telemetry gathering failed: {exc}"],
            )
            async with self.lock:
                self._dispute_store[dispute_id] = record
            await self._save_record_to_db(record)
            return record

        # 3. PayPal Seller Protection Compliance Guardrails
        compliance_result: ComplianceAuditResult = self.compliance_engine.audit_dispute(
            dispute=dispute,
            carrier=carrier_data,
            order=order_data,
        )

        # 4. Visa Compelling Evidence 3.0 (CE 3.0) Network Check
        ce3_result: CE3QualificationResult | None = None
        if tenant.custom_rules.visa_ce3_enabled:
            ce3_result = self.visa_ce3_engine.evaluate_ce3_eligibility(order=order_data)

        # 5. Determine Dispute Fee
        fee = self.order_service.determine_dispute_fee(order_data.merchant_monthly_disputes_count)

        # 6. Horizontal Agentic AI Arbitration & Financial Risk Evaluation
        logger.info(f"[{correlation_id}] Executing AI arbitration for {dispute_id}...")
        decision: ArbitrationDecision = await self.llm_arbitrator.arbitrate(
            dispute=dispute,
            carrier=carrier_data,
            warehouse=wh_data,
            order=order_data,
            dispute_fee=fee,
            compliance=compliance_result,
            ce3=ce3_result,
            billing=billing_data,
        )

        # Apply tenant custom threshold overrides
        if amount > tenant.custom_rules.hitl_order_value_threshold:
            decision.hitl_flagged = True
            rule_reason = (
                f"Tenant rule: Order value (${amount:.2f}) exceeds merchant threshold "
                f"(${tenant.custom_rules.hitl_order_value_threshold:.2f})."
            )
            if rule_reason not in decision.hitl_reasons:
                decision.hitl_reasons.append(rule_reason)

        # 7. Action Dispatching & Automated RMA Enforcement
        pipeline_status = PipelineExecutionStatus.ANALYZING
        action_taken = None
        api_response = None
        outreach_message: str | None = None  # opening message sent to the buyer (INQUIRY stage)
        pdf_path = None
        pdf_sha256: str | None = None
        rma_num = None

        if (
            dispute.dispute_reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED
            and tenant.rma_enabled
            and decision.seller_rights_met
        ):
            rma_details = self.rma_manager.generate_return_label(
                order_id=effective_order_id,
                dispute_id=dispute_id,
                customer_name=order_data.customer_name,
            )
            rma_num = rma_details.rma_number

        if decision.hitl_flagged:
            pipeline_status = PipelineExecutionStatus.FLAGGED_HITL
            action_taken = "FLAGGED_FOR_HITL_REVIEW"
            # Per Decision Matrix: Compile full dossier upfront for human sign-off on CLAIM+ disputes
            if dispute.dispute_stage != DisputeStage.INQUIRY and (
                decision.seller_rights_met or decision.win_probability >= 0.50
            ):
                _, pdf_sha256 = self.pdf_generator.generate_rebuttal_dossier_with_hash(
                    dispute=dispute,
                    decision=decision,
                    carrier=carrier_data,
                    warehouse=wh_data,
                    order=order_data,
                    compliance_result=compliance_result,
                    ce3_result=ce3_result,
                    billing_result=billing_data,
                )
                pdf_path = f"artifacts/dossiers/dispute_{dispute_id}_evidence.pdf"
            logger.info(
                f"[{correlation_id}] Dispute {dispute_id} routed to HITL queue. Reasons: {decision.hitl_reasons}"
            )

        # INQUIRY Stage: Stage-Aware Customer Diplomat & Conversational Settlement Bot
        elif dispute.dispute_stage == DisputeStage.INQUIRY:
            if decision.recommended_action == ArbitrationAction.MAKE_OFFER:
                offer_val = decision.offer_amount or round(amount * 0.50, 2)
                msg = (
                    decision.customer_message
                    or f"Hello {order_data.customer_name}, we would like to offer a 50% courtesy refund of ${offer_val:.2f}."
                )
                api_response = await self.paypal_client.make_offer(
                    dispute_id=dispute_id,
                    offer_amount=offer_val,
                    note=msg,
                    correlation_id=correlation_id,
                )
                action_taken = f"BOT_OFFERED_PARTIAL_REFUND_${offer_val:.2f}"
                outreach_message = msg
            else:
                step, msg, bot_offer_val = self.conversation_bot.advance_negotiation(
                    dispute=dispute,
                    carrier=carrier_data,
                    order=order_data,
                    custom_step1_message=decision.customer_message,
                )
                if step == NegotiationStep.STEP_2_PARTIAL_REFUND and bot_offer_val:
                    api_response = await self.paypal_client.make_offer(
                        dispute_id=dispute_id,
                        offer_amount=bot_offer_val,
                        note=msg,
                        correlation_id=correlation_id,
                    )
                    action_taken = f"BOT_OFFERED_PARTIAL_REFUND_${bot_offer_val:.2f}"
                    outreach_message = msg
                else:
                    api_response = await self.paypal_client.send_message(
                        dispute_id=dispute_id,
                        message=msg,
                        correlation_id=correlation_id,
                    )
                    action_taken = f"BOT_SENT_{step.value}"
                    outreach_message = msg

            pipeline_status = PipelineExecutionStatus.DE_ESCALATED

        # CLAIM Stage: Defend via Cryptographic Dossier or Concede
        elif dispute.dispute_stage in (
            DisputeStage.CLAIM,
            DisputeStage.PRE_ARBITRATION,
            DisputeStage.ARBITRATION,
        ):
            if (
                not compliance_result.is_eligible
                and tenant.custom_rules.auto_concede_unwinnable
                and not decision.seller_rights_met
            ):
                api_response = await self.paypal_client.accept_claim(
                    dispute_id=dispute_id,
                    note=f"Merchant conceded due to Seller Protection policy exclusion: {'; '.join(compliance_result.disqualification_reasons)}",
                    correlation_id=correlation_id,
                )
                action_taken = "CONCEDED_POLICY_EXCLUSION"
                pipeline_status = PipelineExecutionStatus.CONCEDED
                self.accounting_service.log_dispute_concession(
                    dispute_id=dispute_id,
                    merchant_id=tenant.merchant_id,
                    order_id=effective_order_id,
                    amount=amount,
                    dispute_fee=fee,
                )

            elif decision.recommended_action == ArbitrationAction.PROVIDE_EVIDENCE:
                # Compile comprehensive PDF dossier + cryptographic SHA-256 hash
                pdf_bytes, pdf_sha256 = self.pdf_generator.generate_rebuttal_dossier_with_hash(
                    dispute=dispute,
                    decision=decision,
                    carrier=carrier_data,
                    warehouse=wh_data,
                    order=order_data,
                    compliance_result=compliance_result,
                    ce3_result=ce3_result,
                    billing_result=billing_data,
                )
                pdf_path = f"artifacts/dossiers/dispute_{dispute_id}_evidence.pdf"

                api_response = await self.paypal_client.provide_evidence(
                    dispute_id=dispute_id,
                    pdf_bytes=pdf_bytes,
                    notes=decision.rebuttal_statement[:2000],
                    correlation_id=correlation_id,
                )
                action_taken = "PROVIDED_EVIDENCE_DOSSIER"
                pipeline_status = PipelineExecutionStatus.DEFENDED

                # Log ERP accounting win/defense posture
                self.accounting_service.log_dispute_won(
                    dispute_id=dispute_id,
                    merchant_id=tenant.merchant_id,
                    order_id=effective_order_id,
                    amount=amount,
                )

            else:
                # Concession
                api_response = await self.paypal_client.accept_claim(
                    dispute_id=dispute_id,
                    note="Merchant concedes claim upon preliminary review.",
                    correlation_id=correlation_id,
                )
                action_taken = "ACCEPTED_CLAIM_CONCESSION"
                pipeline_status = PipelineExecutionStatus.CONCEDED

                # Log ERP accounting loss write-off
                self.accounting_service.log_dispute_concession(
                    dispute_id=dispute_id,
                    merchant_id=tenant.merchant_id,
                    order_id=effective_order_id,
                    amount=amount,
                    dispute_fee=fee,
                )

        # 8. Build and Store Record
        audit_entries = [
            f"Ingested for merchant '{tenant.merchant_id}' at {datetime.now(UTC).isoformat()}.",
            f"Specialist Agent: {decision.specialist_agent} | Persona: {decision.persona_mode} | LLM Tier: {decision.llm_tier_used}.",
            f"Compliance Audit: {'ELIGIBLE' if compliance_result.is_eligible else 'DISQUALIFIED'}.",
            f"Visa CE 3.0: {'QUALIFIED' if (ce3_result and ce3_result.is_qualified) else 'NOT_APPLICABLE'}.",
            f"Seller Rights Met: {decision.seller_rights_met} | P(win)={decision.win_probability:.2f}, EV=${decision.expected_value:.2f}.",
            f"Action executed: {action_taken}.",
        ]
        if pdf_sha256:
            audit_entries.append(f"Evidentiary Dossier SHA-256: {pdf_sha256}")
        if rma_num:
            audit_entries.append(f"RMA Return Label Generated: {rma_num}")

        record = DisputeRecord(
            dispute_id=dispute_id,
            merchant_id=tenant.merchant_id,
            stage=dispute.dispute_stage,
            reason=dispute.dispute_reason,
            amount=amount,
            currency=dispute.dispute_amount.currency_code or "USD",
            seller_transaction_id=txn_id,
            order_id=effective_order_id,
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
            pdf_dossier_sha256=pdf_sha256,
            paypal_api_response=api_response,
            compliance_eligible=compliance_result.is_eligible,
            compliance_disqualifications=compliance_result.disqualification_reasons,
            visa_ce3_qualified=ce3_result.is_qualified if ce3_result else False,
            rma_number=rma_num,
            specialist_agent=decision.specialist_agent,
            persona_mode=decision.persona_mode,
            llm_tier_used=decision.llm_tier_used,
            seller_rights_met=decision.seller_rights_met,
            reasoning_steps=decision.reasoning_steps,
            telemetry_carrier=carrier_data,
            telemetry_warehouse=wh_data,
            telemetry_order=order_data,
            telemetry_billing=billing_data,
            audit_trail=audit_entries,
            messages=self._opening_messages(outreach_message, decision),
        )

        async with self.lock:
            self._dispute_store[dispute_id] = record
        await self._save_record_to_db(record)

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
        Human reviewer override: Dispatches approved action and records accounting events.
        """
        async with self.lock:
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
            if record.telemetry_carrier and record.telemetry_warehouse and record.telemetry_order:
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
                    specialist_agent=record.specialist_agent or "DisputeSupervisor",
                    persona_mode=record.persona_mode or "ADVERSARIAL_LEGAL_DEFENSE",
                    llm_tier_used=record.llm_tier_used or "TIER_3_DETERMINISTIC_HEURISTIC",
                    reasoning_steps=record.reasoning_steps,
                    seller_rights_met=bool(record.seller_rights_met),
                )
                pdf_bytes, override_sha256 = self.pdf_generator.generate_rebuttal_dossier_with_hash(
                    dispute=dispute_res,
                    decision=arb_dec,
                    carrier=record.telemetry_carrier,
                    warehouse=record.telemetry_warehouse,
                    order=record.telemetry_order,
                    billing_result=record.telemetry_billing,
                )
                record.pdf_dossier_path = f"artifacts/dossiers/dispute_{dispute_id}_evidence.pdf"
                record.pdf_dossier_sha256 = override_sha256
                record.audit_trail.append(f"Evidentiary Dossier SHA-256: {override_sha256}")
                api_response = await self.paypal_client.provide_evidence(
                    dispute_id=dispute_id,
                    pdf_bytes=pdf_bytes,
                    notes=override_req.override_reason,
                )
                action_taken = "HUMAN_OVERRIDE_DEFENDED"
                status = PipelineExecutionStatus.DEFENDED
                self.accounting_service.log_dispute_won(
                    dispute_id=dispute_id,
                    merchant_id=record.merchant_id,
                    order_id=record.order_id or dispute_id,
                    amount=record.amount,
                )

        elif chosen_action == "CONCEDE":
            api_response = await self.paypal_client.accept_claim(
                dispute_id=dispute_id,
                note=f"Conceded following review by {override_req.reviewer_id}: {override_req.override_reason}",
            )
            action_taken = "HUMAN_OVERRIDE_CONCEDED"
            status = PipelineExecutionStatus.CONCEDED
            self.accounting_service.log_dispute_concession(
                dispute_id=dispute_id,
                merchant_id=record.merchant_id,
                order_id=record.order_id or dispute_id,
                amount=record.amount,
                dispute_fee=record.dispute_fee_applied or 15.0,
            )

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

        async with self.lock:
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

        await self._save_record_to_db(record)
        return record

    def get_stats_summary(self, merchant_id: str | None = None) -> DisputeStatsSummary:
        """Calculate executive metrics across ingested disputes."""
        records = list(self._dispute_store.values())
        if merchant_id:
            records = [r for r in records if r.merchant_id == merchant_id]
        total = len(records)
        defended = sum(1 for r in records if r.pipeline_status == PipelineExecutionStatus.DEFENDED)
        conceded = sum(1 for r in records if r.pipeline_status == PipelineExecutionStatus.CONCEDED)
        de_esc = sum(
            1 for r in records if r.pipeline_status == PipelineExecutionStatus.DE_ESCALATED
        )
        hitl = sum(1 for r in records if r.pipeline_status == PipelineExecutionStatus.FLAGGED_HITL)
        tot_amount = sum(r.amount for r in records)
        tot_ev = sum(r.expected_value or 0.0 for r in records)
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


pipeline_instance = DisputePipeline()


def get_dispute_pipeline() -> DisputePipeline:
    """Dependency provider for DisputePipeline."""
    return pipeline_instance
