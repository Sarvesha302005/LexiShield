"""
Disputes Management and HITL Review API.
Provides endpoints to monitor dispute lifecycles, inspect evidence, download PDFs, and perform human overrides.
"""

from datetime import datetime, timezone
import os
import sqlite3
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.core.exceptions import DisputeNotFoundError
from src.models.schemas import (
    BuyerInfo,
    DisputedTransaction,
    DisputeReason,
    DisputeRecord,
    DisputeStage,
    DisputeStatus,
    DisputeStatsSummary,
    HITLOverrideRequest,
    Money,
    PayPalDisputeResource,
    PayPalWebhookEvent,
)
from src.workflows.dispute_pipeline import DisputePipeline, get_dispute_pipeline

router = APIRouter(prefix="/disputes", tags=["Dispute Operations & HITL"])


class SimulateDisputeRequest(BaseModel):
    """Payload to trigger an autonomous dispute resolution simulation."""

    order_id: str | None = Field(None, description="e.g. 'ORD-ZAP-10294' (Marcus Vance)")
    customer_name: str | None = Field(None, description="e.g. 'Marcus Vance'")
    customer_email: str | None = Field(None, description="e.g. 'marcus.vance@gmail.com'")
    reason: str = Field("MERCHANDISE_OR_SERVICE_NOT_RECEIVED", description="Dispute reason code")
    stage: str = Field("CLAIM", description="Stage: 'INQUIRY' or 'CLAIM'")
    amount: float | None = Field(None, description="Disputed amount, defaults to order total")
    merchant_id: str = Field("default-merchant", description="Tenant merchant ID")



@router.get(
    "",
    response_model=list[DisputeRecord],
    summary="List All Disputes",
    description="Retrieve all processed and pending disputes with optional filtering by stage or pipeline status.",
)
async def list_disputes(
    stage: str | None = Query(None, description="Filter by stage: INQUIRY, CLAIM, etc."),
    status: str | None = Query(
        None, description="Filter by status: DEFENDED, CONCEDED, FLAGGED_HITL, etc."
    ),
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> list[DisputeRecord]:
    return pipeline.list_records(stage=stage, status=status)


@router.get(
    "/hitl/queue",
    response_model=list[DisputeRecord],
    summary="Human-in-the-Loop Review Queue",
    description="Lists all disputes flagged for manual operational sign-off (order > $300 or borderline P(win)).",
)
async def get_hitl_queue(
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> list[DisputeRecord]:
    return pipeline.get_hitl_queue()


@router.get(
    "/stats/summary",
    response_model=DisputeStatsSummary,
    summary="Dispute Analytics Summary",
    description="Calculates total defended, conceded, fees avoided, and average win probabilities.",
)
async def get_stats_summary(
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> DisputeStatsSummary:
    return pipeline.get_stats_summary()


@router.get(
    "/{dispute_id}",
    response_model=DisputeRecord,
    summary="Get Dispute Dossier",
    description="Fetches full telemetry, arbitration decision, and audit trail for a dispute.",
)
async def get_dispute(
    dispute_id: str,
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> DisputeRecord:
    record = pipeline.get_record(dispute_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute '{dispute_id}' not found in registry.",
        )
    return record


@router.get(
    "/{dispute_id}/pdf",
    summary="Download Evidentiary Rebuttal PDF",
    description="Returns the compiled ReportLab PDF dossier submitted to PayPal.",
)
async def download_pdf_dossier(
    dispute_id: str,
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> FileResponse:
    record = pipeline.get_record(dispute_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute '{dispute_id}' not found.",
        )

    pdf_path = record.pdf_dossier_path
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No PDF evidentiary dossier found for dispute '{dispute_id}'.",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"PayPal_Evidence_{dispute_id}.pdf",
    )


@router.post(
    "/{dispute_id}/hitl/override",
    response_model=DisputeRecord,
    summary="Submit HITL Human Override",
    description="Human operator confirms or overrides action (DEFEND, CONCEDE, SEND_MESSAGE, MAKE_OFFER).",
)
async def override_hitl_decision(
    dispute_id: str,
    override_req: HITLOverrideRequest,
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> DisputeRecord:
    try:
        return await pipeline.override_hitl(dispute_id=dispute_id, override_req=override_req)
    except DisputeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply HITL override: {exc!s}",
        ) from exc


@router.post(
    "/simulate",
    response_model=DisputeRecord,
    summary="Simulate Inbound PayPal Dispute",
    description="Trigger the live autonomous dispute resolution pipeline against any seeded customer order (e.g. Marcus Vance INR).",
)
async def simulate_dispute(
    req: SimulateDisputeRequest,
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> DisputeRecord:
    """
    Simulates incoming PayPal dispute webhooks for seeded customer orders.
    Pulls carrier telemetry, warehouse QC weights, and serial numbers directly from SQLite,
    executes Seller Protection compliance checks, computes win probability,
    and generates the evidentiary ReportLab PDF rebuttal dossier.
    """
    # 1. Query SQLite for order details
    conn = sqlite3.connect("lexishield.db", timeout=5.0)
    c = conn.cursor()
    row = None
    if req.order_id:
        row = c.execute(
            "SELECT order_id, transaction_id, customer_name, customer_email, total_amount, currency FROM orders WHERE order_id = ? OR transaction_id = ?",
            (req.order_id, req.order_id),
        ).fetchone()
    if not row and (req.customer_name or req.customer_email):
        row = c.execute(
            "SELECT order_id, transaction_id, customer_name, customer_email, total_amount, currency FROM orders WHERE customer_name = ? OR customer_email = ?",
            (req.customer_name or "", req.customer_email or ""),
        ).fetchone()
    conn.close()

    order_id = row[0] if row else (req.order_id or "ORD-ZAP-10294")
    txn_id = row[1] if row else f"TXN-{order_id}"
    buyer_name = row[2] if row else (req.customer_name or "Marcus Vance")
    buyer_email = row[3] if row else (req.customer_email or "marcus.vance@gmail.com")
    amount = req.amount or (float(row[4]) if row else 249.99)
    currency = row[5] if row else "USD"

    # Map reason and stage strings to enum
    try:
        stage_enum = DisputeStage(req.stage.upper())
    except ValueError:
        stage_enum = DisputeStage.CLAIM if "CLAIM" in req.stage.upper() else DisputeStage.INQUIRY

    try:
        reason_enum = DisputeReason(req.reason)
    except ValueError:
        reason_enum = DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED

    sim_id = f"PP-SIM-{uuid.uuid4().hex[:8].upper()}"
    webhook_event = PayPalWebhookEvent(
        id=f"WH-EVT-{uuid.uuid4().hex[:12].upper()}",
        event_version="1.0",
        create_time=datetime.now(timezone.utc).isoformat(),
        resource_type="dispute",
        event_type="CUSTOMER.DISPUTE.CREATED",
        summary=f"Simulated PayPal Dispute for {order_id} ({buyer_name})",
        resource=PayPalDisputeResource(
            dispute_id=sim_id,
            create_time=datetime.now(timezone.utc).isoformat(),
            disputed_transactions=[
                DisputedTransaction(
                    buyer_transaction_id=txn_id,
                    seller_transaction_id=txn_id,
                    gross_amount=Money(currency_code=currency, value=f"{amount:.2f}"),
                    invoice_number=order_id,
                    custom=order_id,
                    buyer=BuyerInfo(name=buyer_name, email=buyer_email),
                )
            ],
            dispute_amount=Money(currency_code=currency, value=f"{amount:.2f}"),
            dispute_stage=stage_enum,
            dispute_reason=reason_enum,
            status=DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
        ),
    )

    record = await pipeline.process_webhook_event(
        event=webhook_event,
        correlation_id=f"CORR-SIM-{sim_id}",
        merchant_id=req.merchant_id,
    )
    return record

