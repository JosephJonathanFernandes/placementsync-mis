"""Pydantic schemas package."""

from app.models.audit_log import AuditLog  # noqa: F401
from app.models.base import Base  # noqa: F401
from app.models.company import Company  # noqa: F401
from app.models.email import Email  # noqa: F401
from app.models.extraction_result import ExtractionResult  # noqa: F401
from app.models.gmail_credentials import GmailCredential  # noqa: F401
from app.models.placement_record import PlacementRecord  # noqa: F401
from app.models.student import Student  # noqa: F401
from app.models.user import User  # noqa: F401

from app.schemas.audit_log import AuditLogOut  # noqa: F401
from app.schemas.company import CompanyOut, CompanyWithPlacements  # noqa: F401
from app.schemas.email import EmailOut, EmailUploadResult  # noqa: F401
from app.schemas.extraction_result import (  # noqa: F401
    ApprovalAction,
    ExtractionResultCreate,
    ExtractionResultOut,
    ExtractionResultWithEmail,
    ExtractedStudent,
)
from app.schemas.placement_record import (  # noqa: F401
    PlacementRecordCreate,
    PlacementRecordOut,
    PlacementRecordUpdate,
    PlacementRecordWithDetails,
)
from app.schemas.student import (  # noqa: F401
    StudentOut,
    StudentCreate,
    StudentUpdate,
    StudentWithPlacements,
)
from app.schemas.user import (  # noqa: F401
    LoginRequest,
    Token,
    TokenData,
    UserBase,
    UserCreate,
    UserOut,
    UserUpdate,
)

__all__ = [
    "AuditLogOut",
    "Base",
    "CompanyOut",
    "CompanyWithPlacements",
    "EmailOut",
    "EmailUploadResult",
    "ExtractionResultCreate",
    "ExtractionResultOut",
    "ExtractionResultWithEmail",
    "ExtractedStudent",
    "LoginRequest",
    "PlacementRecordCreate",
    "PlacementRecordOut",
    "PlacementRecordUpdate",
    "PlacementRecordWithDetails",
    "StudentCreate",
    "StudentOut",
    "StudentUpdate",
    "StudentWithPlacements",
    "Token",
    "TokenData",
    "UserBase",
    "UserCreate",
    "UserOut",
    "UserUpdate",
]
