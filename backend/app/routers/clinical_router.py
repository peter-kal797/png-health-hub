from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..database import get_db
from ..models import Patient, Vaccination, MaternalRecord
from ..schemas import VaccinationIn, VaccinationOut, MaternalRecordIn, MaternalRecordOut
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/clinical", tags=["clinical"])

# ---------------- VACCINATIONS ----------------
@router.post("/vaccinations", response_model=VaccinationOut, status_code=201)
async def add_vaccination(
    body: VaccinationIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    pq = await db.execute(select(Patient).where(Patient.patient_id == body.patient_id))
    if not pq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    vax = Vaccination(**body.model_dump())
    db.add(vax)
    await db.commit()
    await db.refresh(vax)
    return vax

@router.get("/vaccinations/{patient_id}", response_model=list[VaccinationOut])
async def list_vaccinations(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(
        select(Vaccination)
        .where(Vaccination.patient_id == patient_id)
        .order_by(Vaccination.date_administered.desc())
    )
    return q.scalars().all()

# ---------------- MATERNAL HEALTH ----------------
@router.post("/maternal", response_model=MaternalRecordOut, status_code=201)
async def add_maternal_record(
    body: MaternalRecordIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    pq = await db.execute(select(Patient).where(Patient.patient_id == body.patient_id))
    if not pq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    rec = MaternalRecord(**body.model_dump())
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec

@router.get("/maternal/{patient_id}", response_model=list[MaternalRecordOut])
async def list_maternal_records(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(
        select(MaternalRecord)
        .where(MaternalRecord.patient_id == patient_id)
        .order_by(MaternalRecord.visit_date.desc())
    )
    return q.scalars().all()