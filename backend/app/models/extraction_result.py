"""Extraction result model linking an email to extracted placement info."""

import json
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExtractionResult(Base, TimestampMixin):
    __tablename__ = "extraction_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email_id: Mapped[int] = mapped_column(
        ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Integer, nullable=False, default=0)
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending | approved | rejected
    extracted_students: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    raw_extraction: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    missing_fields: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    warnings: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    email: Mapped["Email"] = relationship("Email", back_populates="extraction_results")
    placement_record: Mapped["PlacementRecord | None"] = relationship(
        "PlacementRecord", back_populates="extraction_result", uselist=False
    )
    user: Mapped["User | None"] = relationship("User", uselist=False)

    def get_extracted_students(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.extracted_students or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_extracted_students(self, value: list[dict[str, Any]]) -> None:
        self.extracted_students = json.dumps(value, ensure_ascii=False)

    def get_raw_extraction(self) -> dict[str, Any]:
        try:
            return json.loads(self.raw_extraction or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_raw_extraction(self, value: dict[str, Any]) -> None:
        self.raw_extraction = json.dumps(value, ensure_ascii=False)

    def get_missing_fields(self) -> list[str]:
        try:
            return json.loads(self.missing_fields or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_missing_fields(self, value: list[str]) -> None:
        self.missing_fields = json.dumps(value, ensure_ascii=False)

    def get_warnings(self) -> list[str]:
        try:
            return json.loads(self.warnings or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_warnings(self, value: list[str]) -> None:
        self.warnings = json.dumps(value, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"<ExtractionResult(id={self.id}, email_id={self.email_id}, review_status={self.review_status})>"
