"""Automatic processing pipeline for Gmail messages (Phases 2-3, Phase 7 multi-user).

Fetches new placement-related emails from Gmail, downloads and extracts text
from PDF/DOCX attachments, stores them, classifies them, and runs the
extraction engine on confirmed selection announcements — creating pending
review results for human verification. Nothing is written to the official
placement register until a human approves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.database import get_session_factory
from app.core.logging import logger
from app.models.email import Email
from app.models.extraction_result import ExtractionResult
from app.models.user import User
from app.services.attachment_service.processor import (
    AttachmentText,
    combine_email_and_attachments,
    extract_attachment_text,
)
from app.services.classification_service.classifier import (
    ClassificationResult,
    classify_email,
    is_selection_announcement,
)
from app.services.email_service.parser import ParsedEmail, parse_eml_bytes
from app.services.extraction_service.engine import ExtractionEngine
from app.services.gmail_service.client import (
    GmailMessageSummary,
    build_service,
    decode_raw_message,
    download_attachment,
    get_message_full,
    get_message_raw,
    list_message_attachments,
    list_messages,
    load_credentials,
)

PLACEMENT_SEARCH_QUERY = (
    "selected OR congratulations OR placement OR "
    '"offer letter" OR joining OR shortlisted'
)

engine = ExtractionEngine()


@dataclass
class ProcessSummary:
    fetched: int
    stored: int
    skipped_duplicate: int
    classified_selection: int
    created_review_results: int
    attachment_errors: int
    errors: int


def _email_already_stored(db, external_email_id: str) -> bool:
    return (
        db.query(Email).filter(Email.email_id == external_email_id).first()
        is not None
    )


def _new_db_session():
    return get_session_factory()()


def _store_email(
    db, parsed: ParsedEmail, external_email_id: str, user_id: int | None
) -> Email:
    """Store a parsed Gmail message as an Email record. Returns the Email."""
    from email.utils import parsedate_to_datetime

    received_at = None
    if parsed.date:
        try:
            received_at = parsedate_to_datetime(parsed.date)
        except Exception:
            received_at = None

    email = Email(
        email_id=external_email_id,
        subject=parsed.subject,
        sender=parsed.sender,
        body_text=parsed.body_text,
        body_html=parsed.body_html,
        source="gmail",
        is_processed=False,
        received_at=received_at,
        user_id=user_id,
    )
    db.add(email)
    db.flush()
    return email


def _classify_and_extract(
    db,
    email: Email,
    parsed: ParsedEmail,
    attachment_texts: list[AttachmentText],
    user_id: int | None,
) -> tuple[ClassificationResult, Any]:
    """Classify the email and, if it is a selection announcement, run extraction
    (including attachment text) and create a pending ExtractionResult."""
    combined_body = combine_email_and_attachments(
        parsed.body_text or "", attachment_texts
    )

    combined_parsed = ParsedEmail(
        message_id=parsed.message_id,
        subject=parsed.subject,
        sender=parsed.sender,
        date=parsed.date,
        body_text=combined_body,
        body_html=parsed.body_html,
        attachments=parsed.attachments,
    )

    classification: ClassificationResult = classify_email(
        email.subject, combined_body
    )

    if not is_selection_announcement(classification.category):
        logger.info(
            "Email id=%s classified as %s (not a selection announcement)",
            email.id,
            classification.category,
        )
        return classification, None

    data = engine.extract_from_parsed_email(
        parsed_email=combined_parsed,
        email_date=email.received_at.isoformat() if email.received_at else None,
        classification_category=classification.category,
    )

    from dataclasses import asdict

    result = ExtractionResult(
        email_id=email.id,
        user_id=user_id,
        company_name=data.company_name,
        confidence=int(round(data.confidence * 100)),
        review_status="pending",
    )
    result.set_extracted_students([asdict(s) for s in data.students])
    result.set_raw_extraction(
        {
            "company_name": data.company_name,
            "company_confidence": data.company_confidence,
            "job_role": data.job_role,
            "package": data.package,
            "selection_date": data.selection_date,
            "status": data.status,
            "classification": classification.category,
            "classification_confidence": classification.confidence,
            "source": "gmail",
            "table_rows": data.raw.get("table_rows", []),
            "attachment_files": [a.filename for a in attachment_texts],
        }
    )
    result.set_missing_fields(data.missing_fields)
    result.set_warnings(data.warnings)

    db.add(result)
    email.is_processed = True
    db.commit()
    db.refresh(result)

    logger.info(
        "Created pending extraction result id=%s for gmail email id=%s "
        "(category=%s)",
        result.id,
        email.id,
        classification.category,
    )
    return classification, result


def process_new_messages(
    *,
    user_id: int | None = None,
    query: str = PLACEMENT_SEARCH_QUERY,
    max_results: int = 50,
    label_ids: list[str] | None = None,
) -> ProcessSummary:
    """Fetch new Gmail messages and process them through the extraction pipeline.

    Returns a ProcessSummary with counts. Safe to call repeatedly: already-stored
    messages are skipped (deduplication by Gmail message ID).
    """
    creds = load_credentials(user_id) if user_id else None
    if creds is None:
        logger.warning("No Gmail credentials stored for user %s", user_id)
        return ProcessSummary(
            fetched=0,
            stored=0,
            skipped_duplicate=0,
            classified_selection=0,
            created_review_results=0,
            attachment_errors=0,
            errors=0,
        )

    service = build_service(creds)

    summaries = list_messages(
        service, query=query, max_results=max_results, label_ids=label_ids
    )
    fetched = len(summaries)

    stored = 0
    skipped = 0
    classified_selection = 0
    created_results = 0
    attachment_errors = 0
    errors = 0

    for summary in summaries:
        try:
            db = _new_db_session()
            try:
                if _email_already_stored(db, summary.id):
                    skipped += 1
                    continue

                raw_resp = get_message_raw(service, summary.id)
                raw_bytes = decode_raw_message(raw_resp.get("raw", ""))
                parsed = parse_eml_bytes(raw_bytes)

                attachment_texts: list[AttachmentText] = []
                try:
                    attachment_texts = _download_and_extract_attachments(
                        service, summary.id
                    )
                except Exception:
                    attachment_errors += 1
                    logger.exception(
                        "Attachment processing failed for message %s",
                        summary.id,
                    )

                email = _store_email(db, parsed, summary.id, user_id)
                stored += 1

                classification, result = _classify_and_extract(
                    db, email, parsed, attachment_texts, user_id
                )
                if is_selection_announcement(classification.category):
                    classified_selection += 1
                    if result is not None:
                        created_results += 1
            finally:
                db.close()

        except Exception:
            logger.exception("Failed to process Gmail message %s", summary.id)
            errors += 1

    logger.info(
        "Gmail processing complete: fetched=%d stored=%d skipped=%d "
        "selection=%d results=%d attachment_errors=%d errors=%d",
        fetched,
        stored,
        skipped,
        classified_selection,
        created_results,
        attachment_errors,
        errors,
    )

    return ProcessSummary(
        fetched=fetched,
        stored=stored,
        skipped_duplicate=skipped,
        classified_selection=classified_selection,
        created_review_results=created_results,
        attachment_errors=attachment_errors,
        errors=errors,
    )


def _download_and_extract_attachments(
    service, message_id: str
) -> list[AttachmentText]:
    """Download all attachments from a Gmail message and extract their text."""
    attachments: list[AttachmentText] = []
    try:
        gmail_attachments = list_message_attachments(service, message_id)
    except Exception:
        logger.exception("Failed to list attachments for message %s", message_id)
        return attachments

    for att in gmail_attachments:
        try:
            data = download_attachment(service, message_id, att.attachment_id)
            extracted = extract_attachment_text(
                att.filename, att.mime_type, data
            )
            if extracted is not None:
                attachments.append(extracted)
                logger.info(
                    "Extracted text from attachment %s (%d bytes, %d chars)",
                    att.filename,
                    len(data),
                    len(extracted.text),
                )
        except Exception:
            logger.exception(
                "Failed to process attachment %s in message %s",
                att.filename,
                message_id,
            )
    return attachments


def search_messages(
    service: Any,
    *,
    query: str,
    max_results: int = 50,
    label_ids: list[str] | None = None,
) -> list[GmailMessageSummary]:
    """Public helper to search Gmail messages (used by API routes)."""
    return list_messages(service, query=query, max_results=max_results, label_ids=label_ids)
