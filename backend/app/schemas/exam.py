from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ExamPaperResponse(BaseModel):
    id: str
    title: str
    year: int
    subject: str
    exam_code: str
    paper_type: str
    language: str
    total_questions: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Student view — questions WITHOUT answers
# ---------------------------------------------------------------------------


class PracticeQuestionResponse(BaseModel):
    """Student-facing: question only, no answer."""
    id: str
    exam_paper_id: str
    question_number: str
    sub_question: str
    question_text: str
    question_type: Optional[str] = None
    has_image: bool = False
    image_url: Optional[str] = None  # URL to fetch the cropped image
    order_index: int = 0

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Student view — single question answer (revealed after attempt)
# ---------------------------------------------------------------------------


class QuestionAnswerResponse(BaseModel):
    """Revealed to students after they submit their answer."""
    id: str
    correct_answer: Optional[str] = None
    accepted_answers: Optional[List[str]] = None
    answer_explanation: Optional[str] = None
    marks: Optional[str] = None
    outcome: Optional[int] = None


# ---------------------------------------------------------------------------
# Admin view — questions WITH answers
# ---------------------------------------------------------------------------


class PracticeQuestionWithAnswerResponse(PracticeQuestionResponse):
    """Admin-facing: includes correct answer and marking info."""
    correct_answer: Optional[str] = None
    accepted_answers: Optional[List[str]] = None
    answer_explanation: Optional[str] = None
    marks: Optional[str] = None
    outcome: Optional[int] = None


# ---------------------------------------------------------------------------
# Upload / crawl
# ---------------------------------------------------------------------------


class ExamUploadResponse(BaseModel):
    exam_paper: ExamPaperResponse
    total_questions_parsed: int
    questions: List[PracticeQuestionWithAnswerResponse]


class CrawlRequest(BaseModel):
    url: str
    language: str = "english"
    subject: str = "numeracy"
    exam_code: str = "32406"


class CrawledPaperSummary(BaseModel):
    title: str
    year: int
    total_questions: int
    exam_paper_id: str


class CrawlResponse(BaseModel):
    url: str
    total_pdfs_discovered: int
    total_papers_imported: int
    total_questions_parsed: int
    total_skipped: int = 0
    papers: List[CrawledPaperSummary]
    skipped: List[str] = []
    failed: List[str] = []
    errors: List[str] = []
