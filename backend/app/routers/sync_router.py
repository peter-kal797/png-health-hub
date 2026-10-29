from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Encounter, Patient
from ..schemas import SyncBatch, SyncResult
from ..security.audit import write_audit
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/batch", response_model=SyncResult)
async def sync_batch(
    body: SyncBatch,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    accepted = duplicates = rejected = 0
    details: list[str] = []

    for item in body.encounters:
        pq = await db.execute(select(Patient).where(Patient.patient_id == item.patient_id))
        if not pq.scalar_one_or_none():
            rejected += 1
            details.append(f"{item.client_event_id}: unknown patient {item.patient_id}")
            continue

        if item.client_event_id:
            dup = await db.execute(
                select(Encounter).where(Encounter.client_event_id == item.client_event_id)
            )
            if dup.scalar_one_or_none():
                duplicates += 1
                continue

        enc = Encounter(
            patient_id=item.patient_id,
            facility_name=item.facility_name,
            health_worker_id=item.health_worker_id,
            symptoms=item.symptoms,
            diagnosis=item.diagnosis,
            medications_prescribed=item.medications_prescribed,
            blood_pressure=item.blood_pressure,
            temperature=item.temperature,
            weight=item.weight,
            heart_rate=item.heart_rate,
            is_synced=True,
            client_event_id=item.client_event_id,
        )
        db.add(enc)
        accepted += 1

    await write_audit(
        db,
        event_type="BULK_SYNC",
        operator_id=user.subject,
        target_patient=None,
        facility=user.facility,
        channel="WEB_SYNC",
        payload={
            "device_id": body.device_id,
            "accepted": accepted,
            "duplicates": duplicates,
            "rejected": rejected,
        },
    )
    await db.commit()

    return SyncResult(
        accepted=accepted, duplicates=duplicates, rejected=rejected, details=details
    )