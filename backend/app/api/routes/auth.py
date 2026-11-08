"""Authentication routes (Phase 7).

User authentication:
    POST   /api/auth/register       - Create a new user (admin only, or first user)
    POST   /api/auth/login          - Login with username/password, returns JWT
    POST   /api/auth/logout         - Logout (client clears token)
    GET    /api/auth/me             - Get current user info
    GET    /api/auth/users          - List all users (admin only)
    GET    /api/auth/users/{user_id}- Get a user by ID (admin only)
    PUT    /api/auth/users/{user_id}- Update a user (admin only)
    DELETE /api/auth/users/{user_id}- Delete a user (admin only)

Gmail OAuth 2.0 (Phase 2):
    GET   /api/auth/gmail/authorize      - Get Google authorization URL
    GET   /api/auth/gmail/callback       - OAuth callback (Google redirects here)
    GET   /api/auth/gmail/status         - Gmail connection status
    POST  /api/auth/gmail/disconnect     - Revoke/delete stored credentials
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.api.deps import (
    CurrentUser,
    get_current_user,
    require_admin,
    require_placement_officer,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.models.gmail_credentials import GmailCredential
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    Token,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services.auth_service.service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.gmail_service.client import (
    exchange_code_for_credentials,
    generate_authorize_url,
    load_credentials,
    store_credentials,
    verify_and_consume_state,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# User authentication endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin only, or first user if none exist)",
)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> Any:
    """Register a new user. If no users exist, the first user becomes admin."""
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user_count = db.query(User).count()
    role = "admin" if user_count == 0 else user_in.role
    if user_count > 0 and role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only existing admins can create admin users",
        )

    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered: %s (role=%s)", user.username, user.role)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login with username/password, returns JWT access token",
)
def login(user_in: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Authenticate a user and return a JWT access token."""
    user = db.query(User).filter(User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username}
    )
    logger.info("User logged in: %s", user.username)
    return Token(access_token=access_token)


@router.post(
    "/logout",
    summary="Logout (client should discard the token)",
)
def logout() -> dict[str, str]:
    """Logout endpoint. Token invalidation is handled client-side."""
    return {"message": "Logged out successfully"}


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current authenticated user info",
)
def get_current_user_info(current_user: CurrentUser) -> Any:
    """Get the currently authenticated user's profile."""
    return current_user


@router.get(
    "/users",
    response_model=list[UserOut],
    summary="List all users (admin only)",
)
def list_users(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """List all users. Admin only."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Get a user by ID (admin only)",
)
def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Get a user by ID. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Update a user (admin only)",
)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Update a user's email, role, or active status. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    logger.info("User updated: %s by %s", user.username, current_user.username)
    return user


@router.delete(
    "/users/{user_id}",
    summary="Delete a user (admin only)",
)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a user. Admin only. Cannot delete yourself."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    logger.info("User deleted: %s by %s", user.username, current_user.username)
    return {"message": "User deleted successfully"}


# ---------------------------------------------------------------------------
# Gmail OAuth 2.0 endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/gmail/authorize",
    summary="Get the Gmail OAuth authorization URL",
)
def gmail_authorize(current_user: CurrentUser):
    """Return the Google OAuth consent URL. The frontend redirects the user there."""
    try:
        auth_url, state = generate_authorize_url()
    except RuntimeError as exc:
        logger.exception("Gmail OAuth not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    return {"authorization_url": auth_url, "state": state}


@router.get(
    "/gmail/callback",
    summary="Gmail OAuth callback (Google redirects here)",
)
def gmail_callback(
    current_user: CurrentUser,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """Handle the OAuth callback from Google."""
    frontend_url = settings.frontend_url or "http://localhost:5173"

    if error:
        logger.warning("Gmail OAuth error from Google: %s", error)
        return RedirectResponse(
            url=f"{frontend_url}/settings?gmail=error&reason={error}"
        )

    if not code or not state:
        logger.warning("Gmail OAuth callback missing code or state")
        return RedirectResponse(
            url=f"{frontend_url}/settings?gmail=error&reason=missing_params"
        )

    if not verify_and_consume_state(state):
        logger.warning("Invalid or expired OAuth state token")
        return RedirectResponse(
            url=f"{frontend_url}/settings?gmail=error&reason=invalid_state"
        )

    try:
        creds = exchange_code_for_credentials(code)
    except Exception:
        logger.exception("Failed to exchange OAuth code for credentials")
        return RedirectResponse(
            url=f"{frontend_url}/settings?gmail=error&reason=token_exchange_failed"
        )

    email_address = ""
    try:
        id_token = creds.id_token or {}
        email_address = id_token.get("email", "")
    except Exception:
        email_address = ""

    if not email_address:
        email_address = "connected@gmail.com"

    try:
        # Delete any existing credential for this user
        existing = (
            db.query(GmailCredential)
            .filter(GmailCredential.user_id == current_user.id)
            .first()
        )
        if existing:
            db.delete(existing)
            db.commit()

        # Store new credentials
        scopes = list(creds.scopes or [])
        cred_record = GmailCredential(
            user_id=current_user.id,
            email_address=email_address,
            access_token_encrypted=encrypt(creds.token or ""),
            refresh_token_encrypted=encrypt(creds.refresh_token) if creds.refresh_token else None,
            token_expiry=creds.expiry,
            scopes=",".join(scopes),
            is_active=True,
        )
        db.add(cred_record)
        db.commit()
    except Exception:
        logger.exception("Failed to store Gmail credentials")
        return RedirectResponse(
            url=f"{frontend_url}/settings?gmail=error&reason=storage_failed"
        )

    logger.info(
        "Gmail OAuth complete for user %s (%s)", current_user.username, email_address
    )
    return RedirectResponse(url=f"{frontend_url}/settings?gmail=connected")


@router.get(
    "/gmail/status",
    summary="Check Gmail connection status for current user",
)
def gmail_status(current_user: CurrentUser, db: Session = Depends(get_db)):
    cred = (
        db.query(GmailCredential)
        .filter(
            GmailCredential.user_id == current_user.id,
            GmailCredential.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not cred:
        return {"connected": False, "email_address": None}
    return {
        "connected": True,
        "email_address": cred.email_address,
        "scopes": [s for s in (cred.scopes or "").split(",") if s],
        "token_expiry": cred.token_expiry.isoformat() if cred.token_expiry else None,
    }


@router.post(
    "/gmail/disconnect",
    summary="Disconnect the current user's Gmail account",
)
def gmail_disconnect(current_user: CurrentUser, db: Session = Depends(get_db)):
    cred = (
        db.query(GmailCredential)
        .filter(
            GmailCredential.user_id == current_user.id,
            GmailCredential.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No Gmail account connected"
        )
    db.delete(cred)
    db.commit()
    logger.info("Gmail disconnected for user %s", current_user.username)
    return {"message": "Gmail account disconnected"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def store_credentials_for_user(
    db: Session, user_id: int, email_address: str, creds: Any
) -> None:
    """Store OAuth credentials encrypted at rest for a specific user."""
    scopes = list(creds.scopes or [])
    cred_record = GmailCredential(
        user_id=user_id,
        email_address=email_address,
        access_token_encrypted=encrypt(creds.token or ""),
        refresh_token_encrypted=encrypt(creds.refresh_token) if creds.refresh_token else None,
        token_expiry=creds.expiry,
        scopes=",".join(scopes),
        is_active=True,
    )
    db.add(cred_record)
    db.commit()
