from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Encounter, Patient
from ..schemas import EncounterIn, EncounterOut
from ..security.audit import write_audit
from ..security.rbac import MO_or_admin, CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/encounters", tags=["encounters"])


@router.post("", response_model=EncounterOut, status_code=201)
async def create_encounter(
    body: EncounterIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    pq = await db.execute(select(Patient).where(Patient.patient_id == body.patient_id))
    if not pq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    if body.client_event_id:
        dup = await db.execute(
            select(Encounter).where(Encounter.client_event_id == body.client_event_id)
        )
        existing = dup.scalar_one_or_none()
        if existing:
            return existing

    enc = Encounter(
        patient_id=body.patient_id,
        facility_name=body.facility_name or user.facility,
        health_worker_id=body.health_worker_id,
        symptoms=body.symptoms,
        diagnosis=body.diagnosis,
        medications_prescribed=body.medications_prescribed,
        blood_pressure=body.blood_pressure,
        temperature=body.temperature,
        weight=body.weight,
        heart_rate=body.heart_rate,
        is_synced=True,
        client_event_id=body.client_event_id,
    )
    db.add(enc)
    await db.flush()

    await write_audit(
        db,
        event_type="RECORD_WRITE",
        operator_id=user.subject,
        target_patient=body.patient_id,
        facility=enc.facility_name,
        channel="WEB",
        payload={"encounter_id": str(enc.encounter_id), "diagnosis": body.diagnosis},
    )
    await db.commit()
    await db.refresh(enc)
    return enc


@router.get("/patient/{patient_id}", response_model=list[EncounterOut])
async def list_encounters(
    patient_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    q = await db.execute(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .order_by(Encounter.created_at.desc())
        .limit(min(limit, 100))
    )
    return q.scalars().all()

@router.get("/search/diagnosis")
async def search_diagnosis(
    q: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    from sqlalchemy import func
    query = (
        select(Encounter.patient_id, Encounter.diagnosis, Encounter.created_at, Encounter.facility_name)
        .where(Encounter.diagnosis.ilike(f"%{q}%"))
        .order_by(Encounter.created_at.desc())
        .limit(50)
    )
    res = await db.execute(query)
    return [
        {"patient_id": row[0], "diagnosis": row[1], "date": str(row[2]), "facility": row[3]}
        for row in res.all()
    ]