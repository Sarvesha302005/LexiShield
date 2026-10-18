"""
Pre-Chargeback Alert Intake API (Ethoca Consumer Clarity & Verifi RDR).
Enables zero-fee dispute deflection before chargeback creation.
"""

from fastapi import APIRouter, Depends, status

from src.services.alerts import (
    DeflectionResult,
    PreChargebackDeflectionEngine,
    PreDisputeAlert,
)

router = APIRouter(prefix="/alerts", tags=["Pre-Dispute Alerts (Ethoca & Verifi)"])

# Singleton deflection engine
deflection_engine = PreChargebackDeflectionEngine()


def get_deflection_engine() -> PreChargebackDeflectionEngine:
    return deflection_engine


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    response_model=DeflectionResult,
    summary="Ingest Pre-Chargeback Network Alert",
    description="Listens to Ethoca or Verifi alerts (20-72h prior to chargeback) and executes zero-fee automated refunds.",
)
async def handle_pre_chargeback_alert(
    alert: PreDisputeAlert,
    engine: PreChargebackDeflectionEngine = Depends(get_deflection_engine),
) -> DeflectionResult:
    return await engine.process_alert(alert=alert, auto_refund=True)


@router.get(
    "",
    response_model=list[DeflectionResult],
    summary="List Deflected Alerts",
    description="Returns all pre-dispute alerts and calculated fee savings.",
)
async def list_alerts(
    engine: PreChargebackDeflectionEngine = Depends(get_deflection_engine),
) -> list[DeflectionResult]:
    return engine.list_deflected_alerts()
