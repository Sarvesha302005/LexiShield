"""
PayPal Webhooks Ingestion API.
Verifies cryptographic signature and schedules/processes dispute events through the pipeline.
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.core.exceptions import InvalidSignatureError, WebhookVerificationError
from src.core.security import verify_paypal_webhook_signature
from src.models.schemas import DisputeRecord, PayPalWebhookEvent
from src.workflows.dispute_pipeline import DisputePipeline, get_dispute_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/paypal", tags=["PayPal Webhooks"])


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="PayPal Webhook Intake",
    description="Ingests PayPal webhook events (CUSTOMER.DISPUTE.CREATED, CUSTOMER.DISPUTE.RESOLVED, etc.)",
)
async def handle_paypal_webhook(
    request: Request,
    pipeline: DisputePipeline = Depends(get_dispute_pipeline),
) -> dict[str, Any]:
    """
    Ingest, verify, and process incoming PayPal dispute webhooks.
    """
    correlation_id = request.headers.get("X-Correlation-Id") or f"CORR-{uuid.uuid4().hex[:12]}"
    raw_body = await request.body()

    # 1. Verify PayPal X.509 signature
    try:
        await verify_paypal_webhook_signature(
            headers=dict(request.headers),
            raw_body=raw_body,
        )
    except (InvalidSignatureError, WebhookVerificationError) as exc:
        logger.warning(f"[{correlation_id}] Webhook signature verification rejected: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failure: {exc!s}",
        ) from exc
    except Exception as exc:
        logger.error(f"[{correlation_id}] Unexpected error during webhook verification: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying webhook signature.",
        ) from exc

    # 2. Parse Webhook Event JSON
    try:
        event = PayPalWebhookEvent.model_validate_json(raw_body)
    except Exception as exc:
        logger.error(f"[{correlation_id}] Failed parsing PayPal webhook JSON: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid PayPal webhook schema: {exc!s}",
        ) from exc

    logger.info(f"[{correlation_id}] Webhook verified for event {event.id} ({event.event_type}).")

    # 3. Process through dispute resolution pipeline
    try:
        record: DisputeRecord = await pipeline.process_webhook_event(
            event=event,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        logger.error(f"[{correlation_id}] Pipeline error processing event {event.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution error: {exc!s}",
        ) from exc

    return {
        "status": "PROCESSED",
        "correlation_id": correlation_id,
        "event_id": event.id,
        "event_type": event.event_type,
        "dispute_id": record.dispute_id,
        "pipeline_status": record.pipeline_status.value,
        "action_taken": record.action_taken,
        "win_probability": record.win_probability,
        "hitl_flagged": record.hitl_flagged,
    }
