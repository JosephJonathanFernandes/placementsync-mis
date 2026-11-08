"""Placement record model linking a student to a company."""

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PlacementRecord(Base, TimestampMixin):
    __tablename__ = "placement_records"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "company_id",
            "job_role",
            name="uq_placement_records_student_company_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    package: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selection_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Selected")
    approval_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending | approved | rejected
    email_id: Mapped[int | None] = mapped_column(
        ForeignKey("emails.id", ondelete="SET NULL"), nullable=True
    )
    extraction_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("extraction_results.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    student: Mapped["Student"] = relationship("Student", back_populates="placement_records")
    company: Mapped["Company"] = relationship("Company", back_populates="placement_records")
    extraction_result: Mapped["ExtractionResult | None"] = relationship(
        "ExtractionResult", back_populates="placement_record", uselist=False
    )
    approved_by_user: Mapped["User | None"] = relationship(
        "User", back_populates="placement_records", uselist=False, foreign_keys=[approved_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<PlacementRecord(id={self.id}, student_id={self.student_id}, company_id={self.company_id})>"
