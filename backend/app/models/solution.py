from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.scan_record import ScanRecord


class Solution(Base):
    __tablename__ = "solutions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scan_records.id"), index=True)
    ai_provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    steps: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    related_formula_ids: Mapped[Optional[List[int]]] = mapped_column(
        JSONB, nullable=True
    )
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    knowledge_points: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    scan_record: Mapped["ScanRecord"] = relationship(
        "ScanRecord", back_populates="solutions"
    )
