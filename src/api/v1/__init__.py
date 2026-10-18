"""API v1 router assembly."""

from fastapi import APIRouter

from src.api.v1.alerts import router as alerts_router
from src.api.v1.disputes import router as disputes_router
from src.api.v1.rma import router as rma_router
from src.api.v1.tenants import router as tenants_router
from src.api.v1.webhooks import router as webhooks_router

api_v1_router = APIRouter()
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(disputes_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(rma_router)
