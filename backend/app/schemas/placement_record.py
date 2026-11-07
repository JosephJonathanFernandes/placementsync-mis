"""Placement record schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PlacementRecordBase(BaseModel):
    student_id: int
    company_id: int
    job_role: Optional[str] = None
    package: Optional[str] = None
    selection_date: Optional[datetime] = None
    status: str = "Selected"


class PlacementRecordCreate(PlacementRecordBase):
    email_id: Optional[int] = None
    extraction_result_id: Optional[int] = None


class PlacementRecordUpdate(BaseModel):
    job_role: Optional[str] = None
    package: Optional[str] = None
    selection_date: Optional[datetime] = None
    status: Optional[str] = None
    approval_status: Optional[str] = None


class PlacementRecordOut(PlacementRecordBase):
    id: int
    approval_status: str
    email_id: Optional[int] = None
    extraction_result_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlacementRecordWithDetails(PlacementRecordOut):
    student_name: Optional[str] = None
    student_registration_number: Optional[str] = None
    student_branch: Optional[str] = None
    company_name: Optional[str] = None
