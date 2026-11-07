"""Extraction and review routes (Phase 1 MVP)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json

from dateutil.parser import isoparse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import logger
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.email import Email
from app.models.extraction_result import ExtractionResult
from app.models.placement_record import PlacementRecord
from app.models.student import Student
from app.schemas.extraction_result import (
    ApprovalAction,
    ExtractionResultCreate,
    ExtractionResultOut,
    ExtractionResultWithEmail,
    ExtractedStudent,
)
from app.services.classification_service.classifier import (
    ClassificationResult,
    classify_email,
    is_selection_announcement,
)
from app.services.extraction_service.engine import ExtractionEngine

router = APIRouter(prefix="/api/extraction", tags=["extraction"])
engine = ExtractionEngine()


def _email_not_found(email_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail="Email not found")


@router.post(
    "/run/{email_id}",
    response_model=ExtractionResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="Run extraction on an email and create a review record",
)
def run_extraction(
    email_id: int,
    db: Session = Depends(get_db),
) -> ExtractionResultOut:
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise _email_not_found(email_id)

    # Prevent duplicate extraction results for the same email
    existing = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.email_id == email_id)
        .order_by(ExtractionResult.created_at.desc())
        .first()
    )
    if existing and existing.review_status == "pending":
        return _to_out(existing, email)

    classification: ClassificationResult = classify_email(email.subject, email.body_text)

    data = engine.extract_from_parsed_email(
        parsed_email=email,
        email_date=email.received_at.isoformat() if email.received_at else None,
        classification_category=classification.category,
    )

    result = ExtractionResult(
        email_id=email.id,
        company_name=data.company_name,
        confidence=int(round(data.confidence * 100)),
        review_status="pending",
    )
    from dataclasses import asdict

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
            "table_rows": data.raw.get("table_rows", []),
        }
    )
    result.set_missing_fields(data.missing_fields)
    result.set_warnings(data.warnings)

    db.add(result)
    email.is_processed = True
    db.commit()
    db.refresh(result)


    logger.info(
        "Extraction result id=%s email_id=%s status=%s confidence=%s",
        result.id,
        email_id,
        classification.category,
        data.confidence,
    )
    return _to_out(result, email)


@router.get(
    "/pending",
    response_model=list[ExtractionResultWithEmail],
    summary="List extraction results pending human review",
)
def list_pending(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ExtractionResultWithEmail]:
    results = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.review_status == "pending")
        .order_by(ExtractionResult.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_with_email(r, db) for r in results]


@router.get(
    "/{result_id}",
    response_model=ExtractionResultWithEmail,
    summary="Get an extraction result with its original email",
)
def get_extraction_result(result_id: int, db: Session = Depends(get_db)):
    result = db.query(ExtractionResult).filter(ExtractionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Extraction result not found")
    return _to_with_email(result, db)


@router.post(
    "/{result_id}/approve",
    response_model=ExtractionResultOut,
    summary="Approve an extraction result (creates placement record)",
)
def approve_result(
    result_id: int,
    action: ApprovalAction,
    db: Session = Depends(get_db),
) -> ExtractionResultOut:
    if action.action != "approve":
        raise HTTPException(status_code=400, detail="Use /reject for rejection")

    result = db.query(ExtractionResult).filter(ExtractionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Extraction result not found")
    if result.review_status != "pending":
        raise HTTPException(
            status_code=400, detail=f"Already {result.review_status}"
        )

    raw = result.get_raw_extraction()
    if raw.get("status") == "Shortlisted":
        raise HTTPException(
            status_code=400,
            detail="Shortlisting announcements cannot be approved as placement records. "
                   "Reject this result; shortlisted students are not selected students.",
        )

    email = db.query(Email).filter(Email.id == result.email_id).first()
    students = [
        (s.model_dump() if hasattr(s, "model_dump") else s)
        for s in (action.edited_students or result.get_extracted_students())
    ]
    company_name = action.edited_company or result.company_name

    if not company_name:
        raise HTTPException(
            status_code=400, detail="Company name is required for approval"
        )
    if not students:
        raise HTTPException(
            status_code=400, detail="At least one student is required for approval"
        )

    # Transaction: create/update students, companies, placement records
    created_records: list[PlacementRecord] = []
    try:
        company = db.query(Company).filter_by(name=company_name).first()
        if not company:
            company = Company(name=company_name)
            db.add(company)
            db.flush()

        for s in students:
            student = db.query(Student).filter_by(name=s["name"]).first()
            if not student:
                student = Student(
                    name=s["name"],
                    registration_number=s.get("registration_number"),
                    branch=s.get("branch"),
                )
                db.add(student)
                db.flush()

            sel_date = None
            if raw.get("selection_date"):
                try:
                    sel_date = isoparse(raw.get("selection_date"))
                except Exception:
                    sel_date = None

            record = PlacementRecord(
                student_id=student.id,
                company_id=company.id,
                job_role=s.get("job_role") or raw.get("job_role"),
                package=s.get("package") or raw.get("package"),
                selection_date=sel_date,
                status=raw.get("status", "Selected"),
                approval_status="approved",
                email_id=email.id if email else None,
                extraction_result_id=result.id,
                approved_at=datetime.utcnow(),
                approved_by="reviewer",
            )
            db.add(record)
            created_records.append(record)

        result.review_status = "approved"
        db.add(
            AuditLog(
                table_name="placement_records",
                action="approve",
                new_values=json.dumps(
                    {
                        "extraction_result_id": result.id,
                        "company": company_name,
                        "student_count": len(students),
                    }
                ),
                changed_by="reviewer",
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to approve extraction result %s", result_id)
        raise HTTPException(
            status_code=500, detail="Failed to approve extraction result"
        )

    db.refresh(result)
    logger.info(
        "Approved extraction result id=%s with %d records", result_id, len(created_records)
    )
    return _to_out(result, email)


@router.post(
    "/{result_id}/reject",
    response_model=ExtractionResultOut,
    summary="Reject an extraction result",
)
def reject_result(
    result_id: int,
    action: ApprovalAction,
    db: Session = Depends(get_db),
) -> ExtractionResultOut:
    if action.action != "reject":
        raise HTTPException(status_code=400, detail="Use /approve for approval")

    result = db.query(ExtractionResult).filter(ExtractionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Extraction result not found")
    if result.review_status != "pending":
        raise HTTPException(
            status_code=400, detail=f"Already {result.review_status}"
        )

    result.review_status = "rejected"
    db.add(
        AuditLog(
            table_name="extraction_results",
            action="reject",
            new_values=json.dumps(
                {"extraction_result_id": result.id, "company": result.company_name}
            ),
            changed_by="reviewer",
        )
    )
    db.commit()
    db.refresh(result)

    logger.info("Rejected extraction result id=%s", result_id)
    email = db.query(Email).filter(Email.id == result.email_id).first()
    return _to_out(result, email)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_out(result: ExtractionResult, email: Email | None) -> ExtractionResultOut:
    return ExtractionResultOut(
        id=result.id,
        email_id=result.email_id,
        company_name=result.company_name,
        confidence=result.confidence / 100.0,
        review_status=result.review_status,
        extracted_students=[
            ExtractedStudent(**s) for s in result.get_extracted_students()
        ],
        raw_extraction=result.get_raw_extraction(),
        missing_fields=result.get_missing_fields(),
        warnings=result.get_warnings(),
        created_at=result.created_at,
    )


def _to_with_email(result: ExtractionResult, db: Session) -> ExtractionResultWithEmail:
    email = db.query(Email).filter(Email.id == result.email_id).first()
    base = _to_out(result, email)
    return ExtractionResultWithEmail(
        **base.model_dump(),
        email_subject=email.subject if email else None,
        email_sender=email.sender if email else None,
        email_body=email.body_text if email else None,
    )
