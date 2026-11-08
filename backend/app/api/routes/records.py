"""Placement record routes (Phase 1 + Phase 7 auth)."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.core.logging import logger
from app.models.company import Company
from app.models.extraction_result import ExtractionResult
from app.models.placement_record import PlacementRecord
from app.models.student import Student
from app.schemas.placement_record import (
    PlacementRecordOut,
    PlacementRecordWithDetails,
)

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get(
    "",
    response_model=list[PlacementRecordWithDetails],
    summary="List approved placement records (auth required)",
)
def list_records(
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    company: str | None = Query(None),
    branch: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[PlacementRecordWithDetails]:
    query = (
        db.query(PlacementRecord)
        .options(
            joinedload(PlacementRecord.student),
            joinedload(PlacementRecord.company),
        )
        .filter(PlacementRecord.approval_status == "approved")
    )
    if company:
        query = query.join(PlacementRecord.company).filter(
            Company.name.ilike(f"%{company}%")
        )
    if branch:
        query = query.join(PlacementRecord.student).filter(
            Student.branch.ilike(f"%{branch}%")
        )
    if status:
        query = query.filter(PlacementRecord.status == status)

    records = (
        query.order_by(PlacementRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_with_details(r) for r in records]


@router.get(
    "/stats",
    summary="Dashboard statistics with breakdowns (auth required)",
)
def stats(
    current_user: CurrentUser,
    company: str | None = Query(None),
    branch: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Return dashboard statistics with optional filters."""
    base = db.query(PlacementRecord).filter(
        PlacementRecord.approval_status == "approved"
    )

    if company:
        base = base.join(PlacementRecord.company).filter(
            Company.name.ilike(f"%{company}%")
        )
    if branch:
        base = base.join(PlacementRecord.student).filter(
            Student.branch.ilike(f"%{branch}%")
        )
    if status:
        base = base.filter(PlacementRecord.status == status)
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            base = base.filter(PlacementRecord.selection_date >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            base = base.filter(PlacementRecord.selection_date <= dt)
        except ValueError:
            pass

    total_records = base.count()
    unique_students = (
        base.with_entities(PlacementRecord.student_id).distinct().count()
    )
    total_companies = db.query(Company).count()
    pending_reviews = (
        db.query(ExtractionResult)
        .filter(ExtractionResult.review_status == "pending")
        .count()
    )

    branch_rows = (
        db.query(Student.branch, func.count(PlacementRecord.id))
        .join(PlacementRecord, PlacementRecord.student_id == Student.id)
        .filter(PlacementRecord.approval_status == "approved")
        .group_by(Student.branch)
        .all()
    )
    branch_stats = [
        {"branch": b or "Unknown", "count": int(c)}
        for b, c in branch_rows
    ]

    company_rows = (
        db.query(Company.name, func.count(PlacementRecord.id))
        .join(PlacementRecord, PlacementRecord.company_id == Company.id)
        .filter(PlacementRecord.approval_status == "approved")
        .group_by(Company.name)
        .all()
    )
    company_stats = [
        {"company": c, "count": int(n)}
        for c, n in company_rows
    ]

    package_rows = base.with_entities(PlacementRecord.package).all()
    packages: list[float] = []
    package_histogram: dict[str, int] = {}
    for (pkg,) in package_rows:
        if not pkg:
            continue
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(pkg))
        if m:
            val = float(m.group(1))
            packages.append(val)
            if val < 6:
                bucket = "0-6 LPA"
            elif val < 10:
                bucket = "6-10 LPA"
            elif val < 15:
                bucket = "10-15 LPA"
            elif val < 20:
                bucket = "15-20 LPA"
            else:
                bucket = "20+ LPA"
            package_histogram[bucket] = package_histogram.get(bucket, 0) + 1

    highest_package = max(packages) if packages else None
    average_package = (
        round(sum(packages) / len(packages), 2) if packages else None
    )

    package_distribution = [
        {"range": k, "count": v}
        for k, v in sorted(package_histogram.items())
    ]

    return {
        "total_selected_students": total_records,
        "total_unique_placed_students": unique_students,
        "total_companies": total_companies,
        "pending_email_reviews": pending_reviews,
        "highest_package": highest_package,
        "average_package": average_package,
        "branch_statistics": branch_stats,
        "company_statistics": company_stats,
        "package_distribution": package_distribution,
    }


@router.get(
    "/{record_id}",
    response_model=PlacementRecordWithDetails,
    summary="Get a placement record by ID (auth required)",
)
def get_record(
    current_user: CurrentUser,
    record_id: int,
    db: Session = Depends(get_db),
):
    record = (
        db.query(PlacementRecord)
        .options(
            joinedload(PlacementRecord.student),
            joinedload(PlacementRecord.company),
        )
        .filter(PlacementRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Placement record not found")
    return _to_with_details(record)


def _to_with_details(record: PlacementRecord) -> PlacementRecordWithDetails:
    return PlacementRecordWithDetails(
        id=record.id,
        student_id=record.student_id,
        company_id=record.company_id,
        job_role=record.job_role,
        package=record.package,
        selection_date=record.selection_date,
        status=record.status,
        approval_status=record.approval_status,
        email_id=record.email_id,
        extraction_result_id=record.extraction_result_id,
        approved_at=record.approved_at,
        approved_by=record.approved_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
        student_name=record.student.name if record.student else None,
        student_registration_number=(
            record.student.registration_number if record.student else None
        ),
        student_branch=record.student.branch if record.student else None,
        company_name=record.company.name if record.company else None,
    )
