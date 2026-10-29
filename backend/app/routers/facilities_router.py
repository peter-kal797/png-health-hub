from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Facility
from ..security.rbac import CHW_or_above, CurrentUser

router = APIRouter(prefix="/api/v1/facilities", tags=["facilities"])

@router.get("")
async def list_facilities(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(CHW_or_above),
):
    q = await db.execute(select(Facility).order_by(Facility.name))
    return q.scalars().all()