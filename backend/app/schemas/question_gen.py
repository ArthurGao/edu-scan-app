from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


class GenerateRequest(BaseModel):
    count: int = 3


class GenerateExamRequest(BaseModel):
    count_per_question: int = 3


class ReviewRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("status must be 'approved' or 'rejected'")
        return v


class QuestionEditRequest(BaseModel):
    question_text: Optional[str] = None
    correct_answer: Optional[str] = None
    accepted_answers: Optional[List[str]] = None
    answer_explanation: Optional[str] = None
    question_type: Optional[str] = None


class GeneratedQuestionResponse(BaseModel):
    id: str
    exam_paper_id: str
    question_number: str
    sub_question: str
    question_text: str
    question_type: Optional[str] = None
    correct_answer: Optional[str] = None
    accepted_answers: Optional[List[str]] = None
    answer_explanation: Optional[str] = None
    marks: Optional[str] = None
    outcome: Optional[int] = None
    source: str
    status: str
    source_question_id: Optional[str] = None
    has_image: bool = False
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerateResponse(BaseModel):
    questions: List[GeneratedQuestionResponse]
    total_generated: int


class SyncResponse(BaseModel):
    synced: int
    failed: int
    errors: List[str] = []
