"""Audit log schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    id: int
    table_name: str
    record_id: Optional[int] = None
    action: str
    changed_by: Optional[str] = None
    changed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
