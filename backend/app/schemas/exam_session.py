from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class StartExamRequest(BaseModel):
    exam_paper_id: int
    mode: str  # "timed" | "practice"
    time_limit_minutes: int | None = None


class StartRandomRequest(BaseModel):
    subject: str
    level: int
    question_types: list[str] | None = None
    count: int
    mode: str  # "timed" | "practice"
    time_limit_minutes: int | None = None


class SaveAnswerRequest(BaseModel):
    student_answer: str


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ExamSessionResponse(BaseModel):
    id: int
    session_type: str
    mode: str
    status: str
    total_score: float | None = None
    max_score: float | None = None
    started_at: datetime
    submitted_at: datetime | None = None
    graded_at: datetime | None = None
    question_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ExamAnswerResult(BaseModel):
    question_id: int
    question_text: str
    question_type: str | None = None
    student_answer: str | None = None
    correct_answer: str | None = None
    is_correct: bool | None = None
    score: float | None = None
    max_score: float = 1.0
    grading_method: str | None = None
    answer_explanation: str | None = None
    ai_feedback: str | None = None
    has_image: bool = False
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ExamResultSummary(BaseModel):
    total: int
    correct: int
    partial: int
    incorrect: int


class ExamResultResponse(BaseModel):
    session_id: int
    status: str
    total_score: float | None = None
    max_score: float | None = None
    percentage: float | None = None
    duration_minutes: float | None = None
    summary: ExamResultSummary
    answers: List[ExamAnswerResult]
