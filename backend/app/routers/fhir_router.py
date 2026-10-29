from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.humanname import HumanName

from ..database import get_db
from ..models import Patient
from ..security.rbac import MO_or_admin, CurrentUser

router = APIRouter(prefix="/api/v1/fhir", tags=["fhir"])

@router.get("/Patient/{patient_id}")
async def get_fhir_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    q = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    p = q.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")

    fhir_patient = FHIRPatient(
        id=p.patient_id,
        identifier=[{"system": "urn:oid:2.16.840.1.113883.19.5", "value": p.national_id or p.patient_id}],
        name=[HumanName(family=p.last_name, given=[p.first_name])],
        gender=p.gender.lower() if p.gender in ["M", "F"] else "unknown",
        birthDate=p.date_of_birth.isoformat(),
    )
    return fhir_patient.dict(exclude_none=True)