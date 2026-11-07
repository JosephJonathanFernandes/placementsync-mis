"""Email routes: .eml upload and email listing (Phase 1 MVP)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from email.utils import parsedate_to_datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import logger
from app.models.email import Email
from app.models.extraction_result import ExtractionResult
from app.models.placement_record import PlacementRecord
from app.schemas.email import EmailOut, EmailUploadResult
from app.services.email_service.parser import parse_eml_bytes

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.post(
    "/upload",
    response_model=EmailUploadResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a .eml file",
)
async def upload_eml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> EmailUploadResult:
    """Upload an .eml file, parse it, and store it without running extraction."""
    if not file.filename or not file.filename.lower().endswith(".eml"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .eml files are accepted.",
        )

    data = await file.read()
    try:
        parsed = parse_eml_bytes(data)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to parse .eml file %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse email: {exc}",
        )

    external_id = parsed.message_id
    if not external_id:
        # Deterministic content hash so the same .eml uploaded twice is
        # recognized as the same email (no Message-ID header).
        digest = hashlib.sha256(data).hexdigest()
        external_id = f"content-sha256:{digest}"
    # Avoid re-storing the same email
    existing = db.query(Email).filter(Email.email_id == external_id).first()
    if existing:
        return EmailUploadResult(
            email_id=existing.id,
            external_email_id=existing.email_id,
            subject=existing.subject,
            sender=existing.sender,
            body_preview=(existing.body_text or "")[:200],
            message="Email already uploaded.",
        )

    received_at = None
    if parsed.date:
        try:
            received_at = parsedate_to_datetime(parsed.date)
        except Exception:
            received_at = None

    email = Email(
        email_id=external_id,
        subject=parsed.subject,
        sender=parsed.sender,
        body_text=parsed.body_text,
        body_html=parsed.body_html,
        source="eml_upload",
        is_processed=False,
        received_at=received_at,
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    logger.info(
        "Email uploaded id=%s subject=%r sender=%r",
        email.id,
        parsed.subject,
        parsed.sender,
    )
    return EmailUploadResult(
        email_id=email.id,
        external_email_id=email.email_id,
        subject=email.subject,
        sender=email.sender,
        body_preview=(parsed.body_text or "")[:200],
        message="Email uploaded successfully.",
    )


@router.get(
    "",
    response_model=list[EmailOut],
    summary="List uploaded/fetched emails",
)
def list_emails(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[EmailOut]:
    emails = (
        db.query(Email)
        .order_by(Email.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return emails


@router.get(
    "/{email_id}",
    response_model=EmailOut,
    summary="Get a single email by ID",
)
def get_email(email_id: int, db: Session = Depends(get_db)) -> EmailOut:
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
