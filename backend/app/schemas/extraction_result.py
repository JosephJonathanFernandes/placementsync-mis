"""Extraction result schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ExtractedStudent(BaseModel):
    name: str
    registration_number: Optional[str] = None
    branch: Optional[str] = None
    job_role: Optional[str] = None
    package: Optional[str] = None
    confidence: Optional[float] = None


class ExtractionResultBase(BaseModel):
    company_name: Optional[str] = None
    confidence: float = 0.0
    review_status: str = "pending"


class ExtractionResultCreate(ExtractionResultBase):
    email_id: int
    extracted_students: list[ExtractedStudent] = []
    raw_extraction: dict[str, Any] = {}
    missing_fields: list[str] = []
    warnings: list[str] = []


class ExtractionResultUpdate(BaseModel):
    company_name: Optional[str] = None
    extracted_students: Optional[list[ExtractedStudent]] = None
    raw_extraction: Optional[dict[str, Any]] = None
    missing_fields: Optional[list[str]] = None
    warnings: Optional[list[str]] = None


class ApprovalAction(BaseModel):
    action: str  # approve | reject
    edited_students: Optional[list[ExtractedStudent]] = None
    edited_company: Optional[str] = None
    notes: Optional[str] = None


class ExtractionResultOut(ExtractionResultBase):
    id: int
    email_id: int
    extracted_students: list[ExtractedStudent] = []
    raw_extraction: dict[str, Any] = {}
    missing_fields: list[str] = []
    warnings: list[str] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractionResultWithEmail(ExtractionResultOut):
    email_subject: Optional[str] = None
    email_sender: Optional[str] = None
    email_body: Optional[str] = None
