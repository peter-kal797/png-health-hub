from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Patient, Encounter, Vaccination, MaternalRecord
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

@router.get("/{patient_id}")
async def get_full_report(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    pq = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = pq.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    eq = await db.execute(select(Encounter).where(Encounter.patient_id == patient_id).order_by(Encounter.created_at.desc()))
    encounters = eq.scalars().all()

    vq = await db.execute(select(Vaccination).where(Vaccination.patient_id == patient_id).order_by(Vaccination.date_administered.desc()))
    vaccines = vq.scalars().all()

    mq = await db.execute(select(MaternalRecord).where(MaternalRecord.patient_id == patient_id).order_by(MaternalRecord.visit_date.desc()))
    maternal = mq.scalars().all()

    return {
        "patient": {
            "patient_id": patient.patient_id,
            "name": f"{patient.first_name} {patient.last_name}",
            "dob": str(patient.date_of_birth),
            "gender": patient.gender,
            "blood_type": patient.blood_type,
            "allergies": patient.severe_allergies,
            "province": patient.home_province
        },
        "encounters": [
            {"date": str(e.created_at), "facility": e.facility_name, "symptoms": e.symptoms, "diagnosis": e.diagnosis, "meds": e.medications_prescribed, "bp": e.blood_pressure, "temp": e.temperature, "hr": e.heart_rate, "weight": e.weight}
            for e in encounters
        ],
        "vaccines": [
            {"date": str(v.date_administered), "name": v.vaccine_name, "dose": v.dose_number, "by": v.administered_by}
            for v in vaccines
        ],
        "maternal": [
            {"date": str(m.visit_date), "age": m.gestational_age_weeks, "bp": m.blood_pressure, "weight": m.weight, "fhr": m.fetal_heart_rate, "notes": m.notes}
            for m in maternal
        ]
    }