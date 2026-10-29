from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .jwt_handler import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class CurrentUser:
    def __init__(self, subject: str, role: str, facility: str, full_name: str):
        self.subject = subject
        self.role = role
        self.facility = facility
        self.full_name = full_name


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    try:
        claims = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(
        subject=claims["sub"],
        role=claims["role"],
        facility=claims.get("facility", ""),
        full_name=claims.get("name", ""),
    )


def require_role(*allowed: str):
    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not permitted. Required: {allowed}",
            )
        return user

    return _checker


CHW_or_above = require_role("CommunityHealthWorker", "MedicalOfficer", "SystemAdmin")
MO_or_admin = require_role("MedicalOfficer", "SystemAdmin")
Admin_only = require_role("SystemAdmin")