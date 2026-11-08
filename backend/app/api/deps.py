"""FastAPI dependencies including authentication (Phase 7)."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.auth_service.service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: int | None = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_placement_officer(current_user: User = Depends(get_current_user)) -> User:
    """Dependency requiring placement_officer or admin role."""
    if not current_user.is_placement_officer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Placement officer or admin role required",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency requiring admin role."""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
PlacementOfficerUser = Annotated[User, Depends(require_placement_officer)]
AdminUser = Annotated[User, Depends(require_admin)]

__all__ = [
    "get_db",
    "get_current_user",
    "require_placement_officer",
    "require_admin",
    "CurrentUser",
    "PlacementOfficerUser",
    "AdminUser",
    "oauth2_scheme",
]
