"""Company schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
    name: str


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None


class CompanyOut(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyWithPlacements(CompanyOut):
    placement_count: int = 0
