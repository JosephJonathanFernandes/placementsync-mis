"""Backup & recovery API routes (Phase 5 + Phase 7 auth).

Endpoints:
    POST /api/backup/database   - Download a copy of the SQLite database file
    POST /api/backup/excel      - Download a copy of the Excel placement register
    POST /api/backup/restore    - (Placeholder) Documented restore procedure
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.database import get_engine
from app.core.logging import logger

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.post(
    "/database",
    summary="Download a backup copy of the SQLite database (auth required)",
)
def backup_database(
    current_user: CurrentUser,
):
    """Return the current SQLite database file as a downloadable backup."""
    engine = get_engine()
    db_url = settings.database_url
    if not db_url.startswith("sqlite:///"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database backup is only supported for SQLite.",
        )

    db_path = db_url.replace("sqlite:///", "", 1)
    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database file not found.",
        )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"placement_sync_backup_{timestamp}.db"
    backup_path = os.path.join(os.path.dirname(db_path) or ".", backup_name)

    try:
        shutil.copy2(db_path, backup_path)
    except Exception:
        logger.exception("Failed to copy database for backup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create database backup.",
        )

    logger.info(
        "Database backup created by user %s: %s", current_user.username, backup_path
    )
    return FileResponse(
        path=backup_path,
        media_type="application/x-sqlite3",
        filename=backup_name,
    )


@router.post(
    "/excel",
    summary="Download a backup copy of the Excel placement register (auth required)",
)
def backup_excel(
    current_user: CurrentUser,
):
    """Return the current Excel placement register as a downloadable backup."""
    excel_path = settings.excel_file_path
    if not os.path.exists(excel_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Excel placement register not found.",
        )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"placement_register_backup_{timestamp}.xlsx"
    backup_path = os.path.join(os.path.dirname(excel_path) or ".", backup_name)

    try:
        shutil.copy2(excel_path, backup_path)
    except Exception:
        logger.exception("Failed to copy Excel register for backup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Excel backup.",
        )

    logger.info(
        "Excel backup created by user %s: %s", current_user.username, backup_path
    )
    return FileResponse(
        path=backup_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=backup_name,
    )


@router.post(
    "/restore",
    summary="Restore procedure documentation (auth required)",
)
def restore_procedure(
    current_user: CurrentUser,
):
    """Return documented restore instructions.

    Actual restore is an operational procedure (stop app, replace database file,
    restart app) and is intentionally not exposed as an API endpoint to prevent
    accidental data loss.
    """
    return {
        "message": "Database restore is an operational procedure.",
        "steps": [
            "1. Stop the PlacementSync backend service.",
            "2. Back up the current placement_sync.db (just in case).",
            "3. Replace placement_sync.db with your backup copy.",
            "4. Restart the backend service.",
            "5. Verify data via GET /api/records/stats.",
        ],
        "note": "There is no API endpoint for restore to prevent accidental data loss.",
    }
