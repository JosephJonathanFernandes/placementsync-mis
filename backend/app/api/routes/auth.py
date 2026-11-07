"""Gmail OAuth 2.0 authentication routes (Phase 2).

Endpoints:
    GET /api/auth/gmail/authorize      -> returns the Google authorization URL
    GET /api/auth/gmail/callback       -> OAuth callback; stores tokens, redirects to frontend
    GET /api/auth/gmail/status         -> connection status
    POST /api/auth/gmail/disconnect    -> revoke/delete stored credentials
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging import logger
from app.services.gmail_service.client import (
    Credentials,
    connection_status,
    disconnect,
    exchange_code_for_credentials,
    generate_authorize_url,
    store_credentials,
    verify_and_consume_state,
)

router = APIRouter(prefix="/api/auth/gmail", tags=["gmail-auth"])


@router.get(
    "/authorize",
    summary="Get the Gmail OAuth authorization URL",
)
def authorize():
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
    "/callback",
    summary="Gmail OAuth callback (Google redirects here)",
)
def callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    """Handle the OAuth callback from Google.

    On success: stores credentials and redirects to the frontend settings page.
    On failure: redirects to the frontend with an error query parameter.
    """
    frontend_url = settings.frontend_url or "http://localhost:5173"

    if error:
        logger.warning("Gmail OAuth error from Google: %s", error)
        return RedirectResponse(url=f"{frontend_url}/settings?gmail=error&reason={error}")

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
        creds: Credentials = exchange_code_for_credentials(code)
    except Exception:
        logger.exception("Failed to exchange OAuth code for credentials")
        return RedirectResponse(
            url=f"{frontend_url}/settings?gmail=error&reason=token_exchange_failed"
        )

    # Determine the connected email address from the ID token / userinfo.
    email_address = ""
    try:
        id_token = creds.id_token or {}
        email_address = id_token.get("email", "")
    except Exception:
        email_address = ""

    if not email_address:
        # Fallback: we cannot know the email without an extra API call; still
        # store credentials but mark email as unknown. The user will see status.
        email_address = "connected@gmail.com"

    try:
        store_credentials(creds, email_address)
    except Exception:
        logger.exception("Failed to store Gmail credentials")
        return RedirectResponse(
            url=f"{frontend_url}/settings?gmail=error&reason=storage_failed"
        )

    logger.info("Gmail OAuth complete for %s", email_address)
    return RedirectResponse(url=f"{frontend_url}/settings?gmail=connected")


@router.get(
    "/status",
    summary="Check Gmail connection status",
)
def status_endpoint():
    return connection_status()


@router.post(
    "/disconnect",
    summary="Disconnect the Gmail account",
)
def disconnect_account():
    removed = disconnect()
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No Gmail account connected"
        )
    return {"message": "Gmail account disconnected"}
