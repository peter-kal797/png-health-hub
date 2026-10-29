from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from pydantic import BaseModel

from ..database import get_db
from ..models import Inventory
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/supply", tags=["supply"])


class DispatchIn(BaseModel):
    drug_name: str
    quantity: int
    from_facility: str
    to_facility: str


@router.get("/inventory-all")
async def inventory_all(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Inventory).order_by(Inventory.facility_name, Inventory.drug_name))
    items = q.scalars().all()
    return [
        {
            "drug_name": i.drug_name,
            "quantity": i.quantity,
            "unit": i.unit,
            "facility_name": i.facility_name,
            "low_stock": i.quantity < 100,
        }
        for i in items
    ]


@router.post("/dispatch")
async def dispatch_stock(
    body: DispatchIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(
        select(Inventory).where(
            Inventory.drug_name == body.drug_name,
            Inventory.facility_name == body.from_facility,
        )
    )
    inv = q.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Drug not found at source facility")
    if inv.quantity < body.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock at source facility")

    inv.quantity -= body.quantity

    await db.execute(
        text("""
            INSERT INTO dispatches (drug_name, quantity, from_facility, to_facility, status)
            VALUES (:drug, :qty, :from_f, :to_f, 'IN_TRANSIT')
        """),
        {
            "drug": body.drug_name,
            "qty": body.quantity,
            "from_f": body.from_facility,
            "to_f": body.to_facility,
        },
    )
    await db.commit()
    return {"status": "dispatched", "remaining_at_source": inv.quantity}


@router.get("/dispatches")
async def list_dispatches(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(text("SELECT * FROM dispatches ORDER BY created_at DESC LIMIT 50"))
    return [dict(row._mapping) for row in q.all()]


@router.post("/dispatches/{dispatch_id}/receive")
async def receive_dispatch(
    dispatch_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    dq = await db.execute(text("SELECT * FROM dispatches WHERE id = :id"), {"id": dispatch_id})
    d = dq.first()
    if not d:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    if d.status == "RECEIVED":
        raise HTTPException(status_code=400, detail="Already received")

    iq = await db.execute(
        select(Inventory).where(
            Inventory.drug_name == d.drug_name,
            Inventory.facility_name == d.to_facility,
        )
    )
    inv = iq.scalar_one_or_none()
    if inv:
        inv.quantity += d.quantity
    else:
        db.add(
            Inventory(
                drug_name=d.drug_name,
                quantity=d.quantity,
                unit="tablets",
                facility_name=d.to_facility,
            )
        )

    await db.execute(
        text("UPDATE dispatches SET status = 'RECEIVED', received_at = :t WHERE id = :id"),
        {"t": datetime.now(timezone.utc), "id": dispatch_id},
    )
    await db.commit()
    return {"status": "received"}