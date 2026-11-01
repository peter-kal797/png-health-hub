from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Patient, Encounter
from ..schemas import PatientCreate, PatientOut, EncounterOut
from ..security.audit import write_audit
from ..security.rbac import CHW_or_above, MO_or_admin, CurrentUser

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])

@router.get("", response_model=list[PatientOut])
async def search_patients(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    query = select(Patient).where(
        or_(
            Patient.first_name.ilike(f"%{q}%"),
            Patient.last_name.ilike(f"%{q}%"),
            Patient.patient_id.ilike(f"%{q}%")
        )
    ).limit(20)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=PatientOut, status_code=201)
async def register_patient(
    body: PatientCreate,  # <-- CHANGED: Using schema instead of dict
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    # 1. Check if exists
    existing = await db.execute(select(Patient).where(Patient.patient_id == body.patient_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Patient ID already exists")

    # 2. Create
    new_patient = Patient(
        patient_id=body.patient_id,
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        home_province=body.home_province,
        blood_type=body.blood_type,
        severe_allergies=body.severe_allergies
    )
    db.add(new_patient)
    
    await write_audit(
        db,
        event_type="PATIENT_REGISTER",
        operator_id=user.subject,
        target_patient=body.patient_id,
        facility=user.facility,
        channel="WEB",
        payload={"name": f"{new_patient.first_name} {new_patient.last_name}"},
    )
    await db.commit()
    await db.refresh(new_patient)
    return new_patient

@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = q.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    await write_audit(
        db,
        event_type="RECORD_READ",
        operator_id=user.subject,
        target_patient=patient_id,
        facility=user.facility,
        channel="WEB",
        payload={"patient_id": patient_id, "role": user.role},
    )
    await db.commit()
    return patient

@router.get("/{patient_id}/encounters", response_model=list[EncounterOut])
async def get_patient_history(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .order_by(Encounter.created_at.desc())
    )
    return q.scalars().all()