from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    pass


class ExamPaper(Base):
    __tablename__ = "exam_papers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    subject: Mapped[str] = mapped_column(String(50), index=True)
    exam_code: Mapped[str] = mapped_column(String(50))
    paper_type: Mapped[str] = mapped_column(String(20))  # "exam" | "schedule"
    language: Mapped[str] = mapped_column(String(50), default="english")
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    questions: Mapped[List["PracticeQuestion"]] = relationship(
        "PracticeQuestion", back_populates="exam_paper", cascade="all, delete-orphan"
    )


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_paper_id: Mapped[int] = mapped_column(
        ForeignKey("exam_papers.id", ondelete="CASCADE"), index=True
    )
    question_number: Mapped[str] = mapped_column(String(20))  # "ONE", "TWO"
    sub_question: Mapped[str] = mapped_column(String(10))  # "a", "b", "c"
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # "numeric" | "multichoice" | "explanation"
    correct_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accepted_answers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    answer_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    marks: Mapped[Optional[str]] = mapped_column(
        String(5), nullable=True
    )  # "A" or "H"
    outcome: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    image_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    exam_paper: Mapped["ExamPaper"] = relationship(
        "ExamPaper", back_populates="questions"
    )
