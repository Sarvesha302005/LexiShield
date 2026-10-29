import asyncio
from sqlalchemy import select, func
from src.database.models import TenantModel, DisputeModel, CustomerOrderModel, PreDisputeAlertModel, AccountingEventModel
from src.database.session import AsyncSessionLocal, engine

async def verify():
    async with AsyncSessionLocal() as session:
        t_count = await session.scalar(select(func.count(TenantModel.merchant_id)))
        d_count = await session.scalar(select(func.count(DisputeModel.dispute_id)))
        o_count = await session.scalar(select(func.count(CustomerOrderModel.order_id)))
        a_count = await session.scalar(select(func.count(PreDisputeAlertModel.alert_id)))
        e_count = await session.scalar(select(func.count(AccountingEventModel.event_id)))
        
        print(f"TENANTS: {t_count}")
        print(f"DISPUTES: {d_count}")
        print(f"ORDERS: {o_count}")
        print(f"ALERTS: {a_count}")
        print(f"ACCOUNTING_EVENTS: {e_count}")

        # List all disputes with their stage, reason, and status
        res = await session.execute(select(DisputeModel))
        disputes = res.scalars().all()
        for d in disputes:
            print(f"  -> {d.dispute_id} | Merchant: {d.merchant_id} | Stage: {d.stage} | Reason: {d.reason} | Status: {d.pipeline_status} | Amount: ${d.amount:.2f}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify())

