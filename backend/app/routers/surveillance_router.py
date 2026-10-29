from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Encounter
from ..security.rbac import MO_or_admin, CurrentUser

router = APIRouter(prefix="/api/v1/surveillance", tags=["surveillance"])


@router.get("/anomalies")
async def detect_anomalies(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    recent_q = await db.execute(
        select(Encounter.facility_name, func.count(Encounter.encounter_id))
        .where(Encounter.created_at >= day_ago)
        .group_by(Encounter.facility_name)
    )
    recent = {r[0]: r[1] for r in recent_q.all()}

    baseline_q = await db.execute(
        select(Encounter.facility_name, func.count(Encounter.encounter_id))
        .where(Encounter.created_at >= week_ago, Encounter.created_at < day_ago)
        .group_by(Encounter.facility_name)
    )
    baseline = {r[0]: r[1] / 6.0 for r in baseline_q.all()}

    alerts = []
    for facility, count in recent.items():
        base = baseline.get(facility, 0)
        threshold = max(base * 3, 5)
        if count >= threshold and count > 0:
            alerts.append({
                "facility": facility,
                "recent_24h": count,
                "baseline_avg_24h": round(base, 1),
                "spike_multiplier": round(count / base, 1) if base > 0 else "N/A",
                "severity": "HIGH" if count >= threshold * 2 else "MEDIUM",
            })

    return {
        "generated_at": now.isoformat(),
        "alerts": alerts,
        "total_alerts": len(alerts),
    }


@router.get("/syndromic")
async def syndromic_surveillance(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    week_ago = datetime.utcnow() - timedelta(days=7)
    patterns = {
        "Fever + Rash": "fever",
        "Diarrhea": "diarrhea",
        "Cough + Fever": "cough",
        "Paralysis": "paralysis",
    }
    result = {}
    for label, term in patterns.items():
        q = await db.execute(
            select(func.count(Encounter.encounter_id))
            .where(Encounter.created_at >= week_ago)
            .where(func.lower(Encounter.symptoms).contains(term))
        )
        result[label] = q.scalar() or 0
    return {"period": "last_7_days", "clusters": result}