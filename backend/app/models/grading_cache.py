from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GradingCache(Base):
    __tablename__ = "grading_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("practice_questions.id", ondelete="CASCADE"), nullable=False
    )
    answer_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("question_id", "answer_hash", name="uq_grading_cache_lookup"),
    )
