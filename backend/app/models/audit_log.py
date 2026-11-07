"""Audit log model for tracking changes."""

import json
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_values: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    new_values: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    changed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def get_old_values(self) -> dict[str, Any]:
        try:
            return json.loads(self.old_values or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_new_values(self) -> dict[str, Any]:
        try:
            return json.loads(self.new_values or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, table={self.table_name}, action={self.action})>"
