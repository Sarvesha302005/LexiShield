"""
Multi-Tenant SaaS Onboarding & Custom Rules API.
Manages merchant isolation, BYOK credentials, and custom dispute risk tolerances.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.tenant import TenantManager, TenantNotFoundError, get_tenant_manager
from src.models.tenant import TenantConfig, TenantCustomRules

router = APIRouter(prefix="/tenants", tags=["Multi-Tenant SaaS Management"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TenantConfig,
    summary="Onboard Merchant Tenant",
    description="Registers a new merchant with BYOK credentials (PayPal Client ID/Secret) and custom rule thresholds.",
)
async def onboard_tenant(
    config: TenantConfig,
    manager: TenantManager = Depends(get_tenant_manager),
) -> TenantConfig:
    return manager.register_tenant(config)


@router.get(
    "",
    response_model=list[TenantConfig],
    summary="List All Tenants",
    description="Retrieve all active merchant accounts on the LexiShield platform.",
)
async def list_tenants(
    manager: TenantManager = Depends(get_tenant_manager),
) -> list[TenantConfig]:
    return manager.list_tenants()


@router.get(
    "/{merchant_id}",
    response_model=TenantConfig,
    summary="Get Tenant Configuration",
    description="Fetch tenant details, credentials, and custom automation rules.",
)
async def get_tenant(
    merchant_id: str,
    manager: TenantManager = Depends(get_tenant_manager),
) -> TenantConfig:
    try:
        return manager.get_tenant(merchant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put(
    "/{merchant_id}/rules",
    response_model=TenantConfig,
    summary="Update Tenant Custom Rules",
    description="Configure merchant-specific HITL threshold, defense cutoffs, and CE 3.0 / alert automation.",
)
async def update_tenant_rules(
    merchant_id: str,
    rules: TenantCustomRules,
    manager: TenantManager = Depends(get_tenant_manager),
) -> TenantConfig:
    try:
        return manager.update_tenant_rules(merchant_id=merchant_id, rules=rules)
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
