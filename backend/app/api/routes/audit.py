"""Audit log API routes (Phase 5)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import logger
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get(
    "",
    response_model=list[AuditLogOut],
    summary="List audit log entries",
)
def list_audit_logs(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    table_name: str | None = Query(None),
    action: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    """Return audit log entries, optionally filtered by table or action."""
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.offset(skip).limit(limit).all()
    return [AuditLogOut.model_validate(l) for l in logs]


@router.get(
    "/summary",
    summary="Audit log summary counts",
)
def audit_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return counts of audit actions by table."""
    from sqlalchemy import func

    rows = (
        db.query(AuditLog.table_name, AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.table_name, AuditLog.action)
        .all()
    )
    summary: dict[str, dict[str, int]] = {}
    for table, action, count in rows:
        summary.setdefault(table, {})[action] = int(count)
    logger.info("Audit summary requested: %s", summary)
    return summary
