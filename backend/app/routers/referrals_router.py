from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from ..database import get_db
from ..models import Patient, Referral
from ..schemas import ReferralIn, ReferralOut
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/referrals", tags=["referrals"])


@router.get("/outbound/{facility}")
async def outbound_referrals(
    facility: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(
        select(Referral).where(Referral.from_facility == facility).order_by(Referral.created_at.desc())
    )
    return q.scalars().all()


@router.get("/inbound/{facility}")
async def inbound_referrals(
    facility: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(
        select(Referral)
        .where(Referral.to_facility == facility, Referral.status == "PENDING")
        .order_by(Referral.created_at.desc())
    )
    return q.scalars().all()


@router.post("", response_model=ReferralOut, status_code=201)
async def create_referral(
    body: ReferralIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    pq = await db.execute(select(Patient).where(Patient.patient_id == body.patient_id))
    if not pq.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    ref = Referral(**body.model_dump())
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    return ref


@router.post("/{referral_id}/accept", response_model=ReferralOut)
async def accept_referral(
    referral_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Referral).where(Referral.id == referral_id))
    ref = q.scalar_one_or_none()
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")

    ref.status = "ACCEPTED"
    ref.accepted_by = user.full_name
    ref.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ref)
    return ref