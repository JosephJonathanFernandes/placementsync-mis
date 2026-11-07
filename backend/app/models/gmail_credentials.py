"""Stored Gmail OAuth credentials for a connected account."""

from sqlalchemy import DateTime, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GmailCredentials(Base, TimestampMixin):
    __tablename__ = "gmail_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email_address: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<GmailCredentials(id={self.id}, email={self.email_address!r})>"
