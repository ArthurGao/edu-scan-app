from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SolveRequest(BaseModel):
    subject: Optional[str] = None
    ai_provider: Optional[str] = None
    grade_level: Optional[str] = None


class SolutionStep(BaseModel):
    step: int
    description: str
    formula: Optional[str] = None
    calculation: Optional[str] = None


class FormulaRef(BaseModel):
    id: str
    name: str
    latex: str


class SolutionResponse(BaseModel):
    question_type: str
    knowledge_points: List[str]
    steps: List[SolutionStep]
    final_answer: str
    explanation: Optional[str] = None
    tips: Optional[str] = None


class ScanResponse(BaseModel):
    scan_id: str
    ocr_text: str
    solution: SolutionResponse
    related_formulas: List[FormulaRef]
    created_at: datetime


class ScanRecordResponse(BaseModel):
    id: str
    image_url: Optional[str] = None
    ocr_text: Optional[str]
    subject: Optional[str]
    difficulty: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FollowUpRequest(BaseModel):
    message: str


class FollowUpResponse(BaseModel):
    reply: str
    message_id: Optional[str] = None
    tokens_used: int = 0


class ConversationMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    messages: List[ConversationMessageResponse]
    total_messages: int
