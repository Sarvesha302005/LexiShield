"""
Disputes Management and HITL Review API.
Provides endpoints to monitor dispute lifecycles, inspect evidence, download PDFs, and perform human overrides.
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from src.core.exceptions import DisputeNotFoundError
from src.models.schemas import (
    DisputeRecord,
    DisputeStatsSummary,
    HITLOverrideRequest,
)
from src.workflows.dispute_pipeline import DisputePipeline, get_dispute_pipeline

router = APIRouter(prefix="/disputes", tags=["Dispute Operations & HITL"])


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
