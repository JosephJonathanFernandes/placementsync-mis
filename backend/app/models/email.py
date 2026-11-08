"""Email source model."""

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Email(Base, TimestampMixin):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="eml_upload")
    is_processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    received_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped["User | None"] = relationship("User", back_populates="emails", uselist=False)
    extraction_results: Mapped[list["ExtractionResult"]] = relationship(
        "ExtractionResult", back_populates="email", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Email(id={self.id}, email_id={self.email_id!r}, subject={self.subject!r})>"
