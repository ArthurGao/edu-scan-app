from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.scan import ScanRecordResponse


class CreateMistakeRequest(BaseModel):
    scan_id: str
    notes: Optional[str] = None


class UpdateMistakeRequest(BaseModel):
    notes: Optional[str] = None
    mastered: Optional[bool] = None


class MistakeResponse(BaseModel):
    id: str
    scan_record: ScanRecordResponse
    notes: Optional[str]
    mastered: bool
    review_count: int
    next_review_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
