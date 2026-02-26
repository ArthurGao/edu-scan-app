from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LearningStats(Base):
    __tablename__ = "learning_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "stat_date", "subject", name="uq_user_date_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    subject: Mapped[str] = mapped_column(String(50))
    scan_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    study_minutes: Mapped[int] = mapped_column(Integer, default=0)
    avg_quality_score: Mapped[float] = mapped_column(Float, default=0)
    mastered_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
