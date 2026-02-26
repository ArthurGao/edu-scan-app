from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.solution import Solution


class EvaluationLog(Base):
    __tablename__ = "evaluation_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    solution_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("solutions.id", ondelete="CASCADE"), index=True)
    evaluator_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluator_model: Mapped[str] = mapped_column(String(100), nullable=False)
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    issues: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    solution: Mapped["Solution"] = relationship("Solution", backref="evaluation_logs")
