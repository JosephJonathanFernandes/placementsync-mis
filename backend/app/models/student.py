"""Student model."""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint(
            "registration_number",
            name="uq_students_registration_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    registration_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    branch: Mapped[str | None] = mapped_column(String(100), nullable=True)

    placement_records: Mapped[list["PlacementRecord"]] = relationship(
        "PlacementRecord", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name={self.name!r})>"
