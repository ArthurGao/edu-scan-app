from datetime import date
from pydantic import BaseModel


class DailyStatResponse(BaseModel):
    stat_date: date
    subject: str
    scan_count: int
    correct_count: int
    avg_quality_score: float
    study_minutes: int
    mastered_count: int

    class Config:
        from_attributes = True


class StatsSummaryResponse(BaseModel):
    total_scans: int
    total_mastered: int
    avg_quality: float
    subjects: dict[str, int]
