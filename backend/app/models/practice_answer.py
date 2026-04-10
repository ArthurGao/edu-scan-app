from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PracticeAnswer(Base):
    __tablename__ = "practice_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("practice_questions.id", ondelete="CASCADE"), nullable=False
    )
    student_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    grading_method: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "exact_match" | "ai_grading"
    ai_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    user = relationship("User")
    question = relationship("PracticeQuestion")

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_practice_answers_user_question"),
        Index("ix_practice_answers_user", "user_id"),
        Index("ix_practice_answers_question", "question_id"),
    )
