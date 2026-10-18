"""
Automated Return Merchandise Authorization (RMA) API.
Handles return label generation, carrier tracking, and warehouse inbound inspection gates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.services.rma import RMADetails, RMAManager

router = APIRouter(prefix="/rma", tags=["Automated RMA & Returns"])

# Shared RMA manager singleton
rma_manager_instance = RMAManager()


def get_rma_manager() -> RMAManager:
    return rma_manager_instance


class CreateRMARequest(BaseModel):
    order_id: str
    dispute_id: str
    customer_name: str


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    response_model=RMADetails,
    summary="Generate Prepaid Return Label",
    description="Generates an automated prepaid carrier return label (EasyPost/Shippo) for dispute settlement.",
)
async def generate_return_label(
    req: CreateRMARequest,
    manager: RMAManager = Depends(get_rma_manager),
) -> RMADetails:
    return manager.generate_return_label(
        order_id=req.order_id,
        dispute_id=req.dispute_id,
        customer_name=req.customer_name,
    )


@router.get(
    "/{dispute_id}",
    response_model=RMADetails,
    summary="Get RMA Details",
    description="Retrieve return tracking, carrier label URL, and return status.",
)
async def get_rma(
    dispute_id: str,
    manager: RMAManager = Depends(get_rma_manager),
) -> RMADetails:
    rma = manager.get_rma(dispute_id)
    if not rma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No RMA found for dispute '{dispute_id}'.",
        )
    return rma


@router.post(
    "/{dispute_id}/delivered",
    response_model=RMADetails,
    summary="Mark Return Parcel Received & Inspected",
    description="Records carrier inbound delivery to warehouse and QA verification pass, releasing final refund.",
)
async def mark_return_delivered(
    dispute_id: str,
    manager: RMAManager = Depends(get_rma_manager),
) -> RMADetails:
    rma = manager.mark_inbound_delivery_received(dispute_id)
    if not rma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No RMA found for dispute '{dispute_id}'.",
        )
    return rma
