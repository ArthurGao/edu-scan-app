from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Generation response (questions only, no answers)
# ---------------------------------------------------------------------------


class PracticeQuestionItem(BaseModel):
    """Single generated practice question — student view (no answer)."""
    id: str
    question_text: str
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    difficulty_offset: int = 0
    knowledge_points: Optional[list[str]] = None
    marks: Optional[str] = None
    answered: bool = False
    is_correct: Optional[bool] = None  # Only present if answered

    model_config = ConfigDict(from_attributes=True)


class GeneratePracticeResponse(BaseModel):
    """Response for practice question generation."""
    status: str  # "ready" | "generating" | "error" | "empty"
    scan_id: str
    questions: list[PracticeQuestionItem] = []
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Answer submission
# ---------------------------------------------------------------------------


class SubmitAnswerRequest(BaseModel):
    student_answer: str
    time_spent_seconds: Optional[int] = None


class SubmitAnswerResponse(BaseModel):
    is_correct: bool
    grading_method: str  # "exact_match" | "ai_grading"
    correct_answer: Optional[str] = None
    accepted_answers: Optional[list[str]] = None
    answer_explanation: Optional[str] = None
    ai_feedback: Optional[str] = None
    knowledge_points: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Public question bank
# ---------------------------------------------------------------------------


class PublicQuestionItem(BaseModel):
    """Public question bank listing — no answer."""
    id: str
    question_text: str
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    knowledge_points: Optional[list[str]] = None
    marks: Optional[str] = None
    subject: Optional[str] = None
    usage_count: int = 0
    correct_rate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PublicQuestionListResponse(BaseModel):
    items: list[PublicQuestionItem]
    total: int
    page: int
    pages: int
