"""Gmail API OAuth2 client and message fetching (Phase 2).

All Gmail access is read-only. The application never sends, deletes, or
modifies emails. OAuth credentials/tokens are stored encrypted at rest.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build, Resource

from app.core.config import settings
from app.core.database import get_session_factory
from app.core.logging import logger
from app.core.security import decrypt, encrypt
from app.models.gmail_credentials import GmailCredentials

# Read-only scope: users can read their mail but never send/modify via this app.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# OAuth state store (in-memory, short-lived) for CSRF protection.
_oauth_states: dict[str, float] = {}
OAUTH_STATE_TTL_SECONDS = 600  # 10 minutes


def _flow() -> Flow:
    """Build an OAuth2 Flow for Gmail read-only access."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise RuntimeError(
            "Gmail OAuth is not configured. Set GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET in your environment (.env)."
        )
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def generate_authorize_url() -> tuple[str, str]:
    """Generate the Google OAuth authorization URL and a CSRF state token.

    Returns (authorization_url, state). The caller must store ``state`` and
    verify it in the callback.
    """
    flow = _flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # always request refresh token
    )
    _oauth_states[state] = time.time()
    logger.info("Generated Gmail OAuth authorization URL (state=%s)", state)
    return auth_url, state


def verify_and_consume_state(state: str) -> bool:
    """Verify a CSRF state token and consume it (one-time use)."""
    timestamp = _oauth_states.get(state)
    if timestamp is None:
        return False
    if time.time() - timestamp > OAUTH_STATE_TTL_SECONDS:
        _oauth_states.pop(state, None)
        return False
    _oauth_states.pop(state, None)
    return True


def exchange_code_for_credentials(authorization_code: str) -> Credentials:
    """Exchange an OAuth authorization code for Google Credentials."""
    flow = _flow()
    flow.fetch_token(code=authorization_code)
    creds = flow.credentials
    logger.info("Exchanged OAuth code for Gmail credentials")
    return creds


@dataclass
class StoredCredentials:
    email_address: str
    access_token: str
    refresh_token: str | None
    token_expiry: str | None
    scopes: list[str]


def store_credentials(creds: Credentials, email_address: str) -> None:
    """Store OAuth credentials encrypted at rest (replaces any existing)."""
    from app.core.database import get_session_factory

    scopes = list(creds.scopes or SCOPES)
    db = get_session_factory()()
    try:
        existing = (
            db.query(GmailCredentials)
            .filter(GmailCredentials.email_address == email_address)
            .first()
        )
        if existing:
            existing.access_token_encrypted = encrypt(creds.token or "")
            existing.refresh_token_encrypted = encrypt(creds.refresh_token)
            existing.token_expiry = creds.expiry
            existing.scopes = ",".join(scopes)
            existing.is_active = True
        else:
            db.add(
                GmailCredentials(
                    email_address=email_address,
                    access_token_encrypted=encrypt(creds.token or ""),
                    refresh_token_encrypted=encrypt(creds.refresh_token),
                    token_expiry=creds.expiry,
                    scopes=",".join(scopes),
                    is_active=True,
                )
            )
        db.commit()
        logger.info(
            "Stored Gmail credentials for %s (scopes=%s)", email_address, scopes
        )
    finally:
        db.close()


def load_credentials() -> Credentials | None:
    """Load the active Gmail credentials, refreshing the access token if needed.

    Returns None if no credentials are stored.
    """
    from app.core.database import get_session_factory

    db = get_session_factory()()
    try:
        row = (
            db.query(GmailCredentials)
            .filter(GmailCredentials.is_active == True)  # noqa: E712
            .first()
        )
        if not row:
            return None

        creds = Credentials(
            token=decrypt(row.access_token_encrypted),
            refresh_token=decrypt(row.refresh_token_encrypted),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=[s for s in (row.scopes or "").split(",") if s],
        )
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            creds.refresh(Request())
            # Persist the refreshed access token.
            row.access_token_encrypted = encrypt(creds.token or "")
            row.token_expiry = creds.expiry
            db.commit()
            logger.info("Refreshed Gmail access token for %s", row.email_address)
        return creds
    finally:
        db.close()


def disconnect() -> bool:
    """Revoke and delete stored Gmail credentials. Returns True if removed."""
    from app.core.database import get_session_factory

    db = get_session_factory()()
    try:
        row = (
            db.query(GmailCredentials)
            .filter(GmailCredentials.is_active == True)  # noqa: E712
            .first()
        )
        if not row:
            return False
        email = row.email_address
        db.delete(row)
        db.commit()
        logger.info("Disconnected Gmail account %s", email)
        return True
    finally:
        db.close()


def connection_status() -> dict[str, Any]:
    """Return whether a Gmail account is connected and which email."""
    from app.core.database import get_session_factory

    db = get_session_factory()()
    try:
        row = (
            db.query(GmailCredentials)
            .filter(GmailCredentials.is_active == True)  # noqa: E712
            .first()
        )
        if not row:
            return {"connected": False, "email_address": None}
        return {
            "connected": True,
            "email_address": row.email_address,
            "scopes": [s for s in (row.scopes or "").split(",") if s],
            "token_expiry": row.token_expiry.isoformat() if row.token_expiry else None,
        }
    finally:
        db.close()


def build_service(creds: Credentials) -> Resource:
    """Build a Gmail API resource from credentials."""
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def decode_raw_message(raw: str) -> bytes:
    """Decode a Gmail API base64url-encoded raw message to bytes."""
    return base64.urlsafe_b64decode(raw)


@dataclass
class GmailMessageSummary:
    id: str
    thread_id: str
    snippet: str


def list_messages(
    service: Resource,
    *,
    query: str = "",
    max_results: int = 50,
    label_ids: list[str] | None = None,
) -> list[GmailMessageSummary]:
    """List message IDs matching a Gmail search query."""
    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=query,
            maxResults=max_results,
            labelIds=label_ids,
        )
        .execute()
    )
    messages = result.get("messages", [])
    return [
        GmailMessageSummary(
            id=m["id"],
            thread_id=m.get("threadId", ""),
            snippet="",
        )
        for m in messages
    ]


def get_message_raw(service: Resource, message_id: str) -> dict[str, Any]:
    """Fetch a single message in raw RFC 2822 format."""
    return service.users().messages().get(userId="me", id=message_id, format="raw").execute()


def get_message_full(service: Resource, message_id: str) -> dict[str, Any]:
    """Fetch a single message with full payload (for attachment metadata)."""
    return service.users().messages().get(userId="me", id=message_id, format="full").execute()


@dataclass
class GmailAttachment:
    attachment_id: str
    filename: str
    mime_type: str
    size: int
    message_id: str


def list_message_attachments(
    service: Resource, message_id: str
) -> list[GmailAttachment]:
    """List attachments in a Gmail message by inspecting the full payload."""
    message = get_message_full(service, message_id)
    payload = message.get("payload", {})
    attachments: list[GmailAttachment] = []

    def _walk_parts(parts: list[dict[str, Any]]) -> None:
        for part in parts:
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            filename = part.get("filename", "")
            size = body.get("size", 0)

            if attachment_id and filename:
                attachments.append(
                    GmailAttachment(
                        attachment_id=attachment_id,
                        filename=filename,
                        mime_type=mime_type,
                        size=size,
                        message_id=message_id,
                    )
                )
            # Recurse into multipart parts
            sub_parts = part.get("parts")
            if sub_parts:
                _walk_parts(sub_parts)

    _walk_parts([payload] if payload else [])
    return attachments


def download_attachment(
    service: Resource, message_id: str, attachment_id: str
) -> bytes:
    """Download attachment data from Gmail."""
    result = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    data_b64 = result.get("data", "")
    return base64.urlsafe_b64decode(data_b64)


def list_labels(service: Resource) -> list[dict[str, Any]]:
    """List all Gmail labels for the connected account."""
    result = service.users().labels().list(userId="me").execute()
    return result.get("labels", [])
