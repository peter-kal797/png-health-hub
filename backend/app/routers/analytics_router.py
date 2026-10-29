from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Patient, Encounter, Vaccination, Facility
from ..security.rbac import MO_or_admin, CurrentUser

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    p_count = await db.scalar(select(func.count(Patient.patient_id)))
    e_count = await db.scalar(select(func.count(Encounter.encounter_id)))
    v_count = await db.scalar(select(func.count(Vaccination.id)))

    facility_q = await db.execute(
        select(Encounter.facility_name, func.count(Encounter.encounter_id))
        .group_by(Encounter.facility_name)
    )
    facilities = [{"name": row[0], "count": row[1]} for row in facility_q.all()]

    diag_q = await db.execute(
        select(Encounter.diagnosis, func.count(Encounter.encounter_id))
        .group_by(Encounter.diagnosis)
        .order_by(func.count(Encounter.encounter_id).desc())
        .limit(5)
    )
    diagnoses = [{"name": row[0], "count": row[1]} for row in diag_q.all()]

    # Get list of all facilities for the map
    f_q = await db.execute(select(Facility))
    all_facilities = [{"name": f.name, "province": f.province, "type": f.type} for f in f_q.scalars().all()]

    return {
        "total_patients": p_count,
        "total_encounters": e_count,
        "total_vaccinations": v_count,
        "facilities": facilities,
        "top_diagnoses": diagnoses,
        "all_facilities": all_facilities
    }