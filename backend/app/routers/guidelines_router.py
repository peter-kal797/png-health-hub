from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Guideline
from ..schemas import GuidelineIn, GuidelineOut
from ..security.rbac import CHW_or_above, MO_or_admin, CurrentUser

router = APIRouter(prefix="/api/v1/guidelines", tags=["guidelines"])


@router.get("")
async def list_guidelines(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Guideline).order_by(Guideline.category, Guideline.title))
    items = q.scalars().all()
    return [
        {
            "id": str(g.id),
            "title": g.title,
            "category": g.category,
            "content": g.content,
            "created_at": g.created_at.isoformat(),
        }
        for g in items
    ]


@router.post("")
async def create_guideline(
    body: GuidelineIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(MO_or_admin),
):
    g = Guideline(**body.model_dump())
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return {
        "id": str(g.id),
        "title": g.title,
        "category": g.category,
        "content": g.content,
        "created_at": g.created_at.isoformat(),
    }


@router.get("/search")
async def search_guidelines(
    q: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    result = await db.execute(
        select(Guideline)
        .where(or_(Guideline.title.ilike(f"%{q}%"), Guideline.content.ilike(f"%{q}%")))
        .limit(20)
    )
    items = result.scalars().all()
    return [
        {
            "id": str(g.id),
            "title": g.title,
            "category": g.category,
            "content": g.content,
            "created_at": g.created_at.isoformat(),
        }
        for g in items
    ]