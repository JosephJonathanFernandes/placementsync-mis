"""Student schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StudentBase(BaseModel):
    name: str
    registration_number: Optional[str] = None
    branch: Optional[str] = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    branch: Optional[str] = None


class StudentOut(StudentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentWithPlacements(StudentOut):
    placement_count: int = 0
