"""User model for multi-user authentication (Phase 7)."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Application user with role-based access control."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")  # admin | placement_officer | viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # One Gmail credential per user
    gmail_credential: Mapped["GmailCredential | None"] = relationship(
        "GmailCredential", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    # Emails uploaded/fetched by this user
    emails: Mapped[list["Email"]] = relationship(
        "Email", back_populates="user", cascade="all, delete-orphan"
    )
    # Placement records approved by this user
    placement_records: Mapped[list["PlacementRecord"]] = relationship(
        "PlacementRecord", back_populates="approved_by_user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r}, role={self.role})>"

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_placement_officer(self) -> bool:
        return self.role in ("admin", "placement_officer")

    def is_viewer(self) -> bool:
        return self.role == "viewer"
