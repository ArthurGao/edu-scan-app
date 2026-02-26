from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.solution import Solution
    from app.models.user import User


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    image_url: Mapped[str] = mapped_column(String(500))
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="scan_records")
    solutions: Mapped[List["Solution"]] = relationship(
        "Solution", back_populates="scan_record", cascade="all, delete-orphan"
    )
