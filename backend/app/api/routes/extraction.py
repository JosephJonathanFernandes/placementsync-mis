"""Extraction and review routes (Phase 1 + Phase 7 auth)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from dateutil.parser import isoparse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, PlacementOfficerUser
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


@router.post(
    "/run/{email_id}",
    response_model=ExtractionResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="Run extraction on an email and create a review record (auth required)",
)
def run_extraction(
    current_user: CurrentUser,
    email_id: int,
    db: Session = Depends(get_db),
) -> ExtractionResultOut:
    email = (
        db.query(Email)
        .filter(Email.id == email_id, Email.user_id == current_user.id)
        .first()
    )
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    existing = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.email_id == email_id)
        .order_by(ExtractionResult.created_at.desc())
        .first()
    )
    if existing and existing.review_status == "pending":
        return _to_out(existing, email)

    classification: ClassificationResult = classify_email(
        email.subject, email.body_text
    )

    data = engine.extract_from_parsed_email(
        parsed_email=email,
        email_date=email.received_at.isoformat() if email.received_at else None,
        classification_category=classification.category,
    )

    result = ExtractionResult(
        email_id=email.id,
        user_id=current_user.id,
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
        "Extraction result id=%s email_id=%s status=%s confidence=%s user_id=%s",
        result.id,
        email_id,
        classification.category,
        data.confidence,
        current_user.id,
    )
    return _to_out(result, email)


@router.get(
    "/pending",
    response_model=list[ExtractionResultWithEmail],
    summary="List extraction results pending human review (auth required)",
)
def list_pending(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ExtractionResultWithEmail]:
    results = (
        db.query(ExtractionResult)
        .join(ExtractionResult.email)
        .filter(Email.user_id == current_user.id)
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
    summary="Get an extraction result with its original email (auth required)",
)
def get_extraction_result(
    current_user: CurrentUser,
    result_id: int,
    db: Session = Depends(get_db),
):
    result = (
        db.query(ExtractionResult)
        .join(ExtractionResult.email)
        .filter(ExtractionResult.id == result_id, Email.user_id == current_user.id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Extraction result not found")
    return _to_with_email(result, db)


@router.post(
    "/{result_id}/approve",
    response_model=ExtractionResultOut,
    summary="Approve an extraction result (creates placement record) (placement officer only)",
)
def approve_result(
    current_user: PlacementOfficerUser,
    result_id: int,
    action: ApprovalAction,
    db: Session = Depends(get_db),
) -> ExtractionResultOut:
    if action.action != "approve":
        raise HTTPException(status_code=400, detail="Use /reject for rejection")

    result = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.id == result_id)
        .first()
    )
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
                approved_by_user_id=current_user.id,
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
                changed_by=current_user.username,
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
        "Approved extraction result id=%s with %d records by user %s",
        result_id,
        len(created_records),
        current_user.username,
    )
    return _to_out(result, email)


@router.post(
    "/{result_id}/reject",
    response_model=ExtractionResultOut,
    summary="Reject an extraction result (placement officer only)",
)
def reject_result(
    current_user: PlacementOfficerUser,
    result_id: int,
    action: ApprovalAction,
    db: Session = Depends(get_db),
) -> ExtractionResultOut:
    if action.action != "reject":
        raise HTTPException(status_code=400, detail="Use /approve for approval")

    result = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.id == result_id)
        .first()
    )
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
            changed_by=current_user.username,
        )
    )
    db.commit()
    db.refresh(result)

    logger.info("Rejected extraction result id=%s by user %s", result_id, current_user.username)
    email = db.query(Email).filter(Email.id == result.email_id).first()
    return _to_out(result, email)


@router.post(
    "/bulk/approve",
    response_model=dict,
    summary="Bulk approve multiple extraction results (placement officer only)",
)
def bulk_approve(
    current_user: PlacementOfficerUser,
    result_ids: list[int],
    edited_company: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Approve multiple extraction results in a single request."""
    results = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.id.in_(result_ids))
        .all()
    )

    if not results:
        raise HTTPException(status_code=404, detail="No extraction results found")

    approved_count = 0
    errors: list[str] = []

    for result in results:
        if result.review_status != "pending":
            errors.append(f"Result {result.id} is already {result.review_status}")
            continue

        raw = result.get_raw_extraction()
        if raw.get("status") == "Shortlisted":
            errors.append(f"Result {result.id} is a shortlisting announcement")
            continue

        email = db.query(Email).filter(Email.id == result.email_id).first()
        students = result.get_extracted_students()
        company_name = edited_company or result.company_name

        if not company_name:
            errors.append(f"Result {result.id}: company name is required")
            continue
        if not students:
            errors.append(f"Result {result.id}: at least one student is required")
            continue

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
                    approved_by=current_user.username,
                    approved_by_user_id=current_user.id,
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
                    changed_by=current_user.username,
                )
            )
            approved_count += 1
        except Exception:
            logger.exception("Failed to approve extraction result %s", result.id)
            errors.append(f"Result {result.id}: approval failed")
            continue

    db.commit()

    logger.info(
        "Bulk approved %d results by user %s",
        approved_count,
        current_user.username,
    )

    return {
        "message": f"Bulk approval complete: {approved_count} approved",
        "approved_count": approved_count,
        "errors": errors,
    }


@router.post(
    "/bulk/reject",
    response_model=dict,
    summary="Bulk reject multiple extraction results (placement officer only)",
)
def bulk_reject(
    current_user: PlacementOfficerUser,
    result_ids: list[int],
    db: Session = Depends(get_db),
) -> dict:
    """Reject multiple extraction results in a single request."""
    results = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.id.in_(result_ids))
        .all()
    )

    if not results:
        raise HTTPException(status_code=404, detail="No extraction results found")

    rejected_count = 0

    for result in results:
        if result.review_status != "pending":
            continue
        result.review_status = "rejected"
        db.add(
            AuditLog(
                table_name="extraction_results",
                action="reject",
                new_values=json.dumps(
                    {"extraction_result_id": result.id, "company": result.company_name}
                ),
                changed_by=current_user.username,
            )
        )
        rejected_count += 1

    db.commit()

    logger.info(
        "Bulk rejected %d results by user %s",
        rejected_count,
        current_user.username,
    )

    return {
        "message": f"Bulk rejection complete: {rejected_count} rejected",
        "rejected_count": rejected_count,
    }


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
