from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..database import get_db
from ..models import Patient, Encounter, Vaccination
from ..security.rbac import MO_or_admin, CurrentUser

router = APIRouter(prefix="/api/v1/dhis2", tags=["dhis2"])


@router.get("/summary")
async def dhis2_summary(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    province_q = await db.execute(
        select(Patient.home_province, func.count(Patient.patient_id)).group_by(Patient.home_province)
    )
    by_province = [{"province": r[0], "count": r[1]} for r in province_q.all()]

    diag_q = await db.execute(
        select(Encounter.diagnosis, func.count(Encounter.encounter_id))
        .group_by(Encounter.diagnosis)
        .order_by(func.count(Encounter.encounter_id).desc())
        .limit(20)
    )
    by_diagnosis = [{"diagnosis": r[0], "count": r[1]} for r in diag_q.all()]

    vax_q = await db.execute(
        select(Vaccination.vaccine_name, func.count(Vaccination.id)).group_by(Vaccination.vaccine_name)
    )
    by_vaccine = [{"vaccine": r[0], "count": r[1]} for r in vax_q.all()]

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "reporting_period": datetime.utcnow().strftime("%Y-%m"),
        "dataElements": {
            "totalPatients": await db.scalar(select(func.count(Patient.patient_id))),
            "totalEncounters": await db.scalar(select(func.count(Encounter.encounter_id))),
            "totalVaccinations": await db.scalar(select(func.count(Vaccination.id))),
        },
        "byProvince": by_province,
        "byDiagnosis": by_diagnosis,
        "byVaccine": by_vaccine,
    }