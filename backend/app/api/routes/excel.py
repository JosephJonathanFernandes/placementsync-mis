"""Excel export routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import os

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.models.company import Company
from app.models.placement_record import PlacementRecord
from app.models.student import Student
from app.services.excel_service.generator import ExcelService

router = APIRouter(prefix="/api/excel", tags=["excel"])


@router.get(
    "/export",
    summary="Generate/download the placement register Excel file",
)
def export_excel(
    company: str | None = None,
    branch: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(PlacementRecord).filter(PlacementRecord.approval_status == "approved")
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

    records = query.order_by(PlacementRecord.created_at.desc()).all()
    payload = [
        {
            "student_name": r.student.name if r.student else "",
            "registration_number": r.student.registration_number if r.student else "",
            "branch": r.student.branch if r.student else "",
            "company_name": r.company.name if r.company else "",
            "job_role": r.job_role or "",
            "package": r.package or "",
            "selection_date": (
                r.selection_date.isoformat() if r.selection_date else ""
            ),
            "status": r.status,
        }
        for r in records
    ]

    service = ExcelService(settings.excel_file_path)
    result = service.generate_from_records(payload, overwrite=False)
    logger.info(
        "Excel export: added=%d skipped=%d total=%d",
        result["added"],
        result["skipped_duplicates"],
        result["total_rows"],
    )

    if not os.path.exists(result["file_path"]):
        raise HTTPException(status_code=500, detail="Excel file could not be generated")

    return FileResponse(
        path=result["file_path"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="placement_register.xlsx",
    )


@router.get(
    "/download",
    summary="Download the existing placement register if present",
)
def download_excel():
    if not os.path.exists(settings.excel_file_path):
        raise HTTPException(status_code=404, detail="No placement register found")
    return FileResponse(
        path=settings.excel_file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="placement_register.xlsx",
    )
