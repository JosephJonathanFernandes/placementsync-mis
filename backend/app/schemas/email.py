"""Email schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmailBase(BaseModel):
    subject: Optional[str] = None
    sender: Optional[str] = None


class EmailOut(EmailBase):
    id: int
    email_id: str
    source: str
    is_processed: bool
    received_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailUploadResult(BaseModel):
    email_id: int
    external_email_id: str
    subject: Optional[str]
    sender: Optional[str]
    body_preview: Optional[str]
    message: str
