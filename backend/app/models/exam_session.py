from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.exam_paper import ExamPaper, PracticeQuestion
    from app.models.user import User


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exam_paper_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("exam_papers.id", ondelete="SET NULL"), nullable=True
    )  # null for random practice
    session_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "real_exam" | "random_practice"
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "timed" | "practice"
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # null for practice mode
    status: Mapped[str] = mapped_column(
        String(20), default="in_progress", server_default="in_progress"
    )  # "in_progress" | "submitted" | "graded"
    total_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    graded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    filter_criteria: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Random quiz filters: {subject, level, question_types, count}
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    exam_paper: Mapped[Optional["ExamPaper"]] = relationship("ExamPaper")
    answers: Mapped[List["ExamAnswer"]] = relationship(
        "ExamAnswer", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_exam_sessions_user_status", "user_id", "status"),
    )


class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("practice_questions.id", ondelete="CASCADE"), nullable=False
    )
    student_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[float] = mapped_column(Float, default=1.0)
    grading_method: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # "exact_match" | "ai_grading"
    ai_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    session: Mapped["ExamSession"] = relationship(
        "ExamSession", back_populates="answers"
    )
    question: Mapped["PracticeQuestion"] = relationship("PracticeQuestion")

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_exam_answer_session_question"),
        Index("ix_exam_answers_session", "session_id"),
    )
