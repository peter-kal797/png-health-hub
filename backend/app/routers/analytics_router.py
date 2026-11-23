from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Patient, Encounter
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    # 1. Count total patients
    patient_count = await db.scalar(select(func.count()).select_from(Patient))
    
    # 2. Count total encounters
    encounter_count = await db.scalar(select(func.count()).select_from(Encounter))
    
    # 3. Get top 5 diagnoses
    diag_query = (
        select(Encounter.diagnosis, func.count(Encounter.diagnosis).label("count"))
        .where(Encounter.diagnosis.isnot(None))
        .group_by(Encounter.diagnosis)
        .order_by(func.count(Encounter.diagnosis).desc())
        .limit(5)
    )
    diag_res = await db.execute(diag_query)
    top_diagnoses = [{"diagnosis": row[0], "count": row[1]} for row in diag_res.all()]

    return {
        "total_patients": patient_count or 0,
        "total_encounters": encounter_count or 0,
        "top_diagnoses": top_diagnoses
    }