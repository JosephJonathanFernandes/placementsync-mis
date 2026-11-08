"""Stored Gmail OAuth credentials for a connected account (Phase 7 multi-user)."""

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class GmailCredential(Base, TimestampMixin):
    """Encrypted Gmail OAuth tokens for a single user."""

    __tablename__ = "gmail_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="gmail_credential")

    def __repr__(self) -> str:
        return f"<GmailCredential(id={self.id}, email={self.email_address!r}, user_id={self.user_id})>"
