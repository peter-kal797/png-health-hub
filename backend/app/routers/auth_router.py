from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import bcrypt

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, TokenResponse
from ..security.jwt_handler import create_access_token
from ..security.rbac import Admin_only, CurrentUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(User).where(User.username == body.username, User.is_active.is_(True))
    )
    user = q.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    token = create_access_token(
        subject=str(user.user_id),
        role=user.role,
        facility=user.facility_name,
        full_name=user.full_name,
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        full_name=user.full_name,
        facility=user.facility_name,
    )

class SeedUser(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    facility_name: str

@router.post("/seed", include_in_schema=False)
async def seed_user(body: SeedUser, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        return {"status": "exists"}
    db.add(
        User(
            username=body.username,
            password_hash=_hash_password(body.password),
            full_name=body.full_name,
            role=body.role,
            facility_name=body.facility_name,
        )
    )
    await db.commit()
    return {"status": "created"}

class CreateUserRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    facility_name: str

@router.post("/users")
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(Admin_only),
):
    if body.role not in ["CommunityHealthWorker", "MedicalOfficer", "SystemAdmin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    
    new_user = User(
        username=body.username,
        password_hash=_hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        facility_name=body.facility_name,
    )
    db.add(new_user)
    await db.commit()
    return {"status": "created", "username": body.username, "role": body.role}