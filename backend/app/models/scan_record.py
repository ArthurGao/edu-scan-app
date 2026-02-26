from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

if TYPE_CHECKING:
    from app.models.solution import Solution
    from app.models.user import User


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    problem_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    knowledge_points: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True) if Vector else None
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="scan_records")
    solutions: Mapped[List["Solution"]] = relationship(
        "Solution", back_populates="scan_record", cascade="all, delete-orphan"
    )
