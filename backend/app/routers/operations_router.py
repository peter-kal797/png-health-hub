from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..database import get_db
from ..models import Patient, Inventory, Bill
from ..schemas import InventoryIn, InventoryOut, BillIn, BillOut
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


# ---------------- PHARMACY ----------------
@router.get("/inventory")
async def list_inventory(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Inventory).order_by(Inventory.drug_name))
    items = q.scalars().all()
    return [
        {
            "id": str(i.id),
            "drug_name": i.drug_name,
            "quantity": i.quantity,
            "unit": i.unit,
            "facility_name": i.facility_name,
            "last_updated": i.last_updated.isoformat(),
        }
        for i in items
    ]


@router.post("/inventory")
async def add_inventory(
    body: InventoryIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    existing = await db.execute(select(Inventory).where(Inventory.drug_name == body.drug_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Drug already exists in inventory")

    item = Inventory(**body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {
        "id": str(item.id),
        "drug_name": item.drug_name,
        "quantity": item.quantity,
        "unit": item.unit,
        "facility_name": item.facility_name,
        "last_updated": item.last_updated.isoformat(),
    }


# ---------------- BILLING ----------------
@router.get("/bills/{patient_id}")
async def list_bills(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Bill).where(Bill.patient_id == patient_id).order_by(Bill.created_at.desc()))
    bills = q.scalars().all()
    return [
        {
            "id": str(b.id),
            "patient_id": b.patient_id,
            "description": b.description,
            "amount": float(b.amount),
            "status": b.status,
            "created_at": b.created_at.isoformat(),
        }
        for b in bills
    ]


@router.post("/bills")
async def add_bill(
    body: BillIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    pq = await db.execute(select(Patient).where(Patient.patient_id == body.patient_id))
    if not pq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    bill = Bill(**body.model_dump())
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    return {
        "id": str(bill.id),
        "patient_id": bill.patient_id,
        "description": bill.description,
        "amount": float(bill.amount),
        "status": bill.status,
        "created_at": bill.created_at.isoformat(),
    }


# ---------------- EXTRA FEATURES ----------------
@router.get("/low-stock")
async def low_stock(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Inventory).where(Inventory.quantity < 100).order_by(Inventory.quantity))
    items = q.scalars().all()
    return [
        {"drug_name": i.drug_name, "quantity": i.quantity, "unit": i.unit} for i in items
    ]


@router.get("/bills/{patient_id}/print")
async def print_bill(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    pq = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = pq.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    bq = await db.execute(select(Bill).where(Bill.patient_id == patient_id).order_by(Bill.created_at.desc()))
    bills = bq.scalars().all()

    total = sum(float(b.amount) for b in bills)
    rows = "".join(
        f"<tr><td>{b.created_at.strftime('%Y-%m-%d')}</td><td>{b.description}</td><td>PGK {float(b.amount):.2f}</td><td>{b.status}</td></tr>"
        for b in bills
    )

    html = f"""
    <html><head><title>Bill - {patient.patient_id}</title>
    <style>
      body {{ font-family: system-ui, sans-serif; padding: 40px; color: #000; max-width: 800px; margin: 0 auto; }}
      h1 {{ color: #0ea5e9; border-bottom: 2px solid #0ea5e9; padding-bottom: 10px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
      th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #eee; }}
      th {{ background: #f8fafc; color: #666; }}
      .total {{ font-size: 24px; font-weight: bold; color: #ef4444; text-align: right; margin-top: 24px; }}
    </style></head><body>
    <h1>Patient Billing Statement</h1>
    <p><strong>Name:</strong> {patient.first_name} {patient.last_name}</p>
    <p><strong>SevisPass ID:</strong> {patient.patient_id}</p>
    <table><tr><th>Date</th><th>Description</th><th>Amount</th><th>Status</th></tr>{rows}</table>
    <div class="total">TOTAL: PGK {total:.2f}</div>
    <p style="margin-top: 40px; font-size: 12px; color: #999;">Generated by PNG Health Hub on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </body></html>
    """
    return {"html": html}