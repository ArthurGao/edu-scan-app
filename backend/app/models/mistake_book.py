from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.scan_record import ScanRecord
    from app.models.user import User


class MistakeBook(Base):
    __tablename__ = "mistake_books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scan_records.id"), index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="mistake_books")
    scan_record: Mapped["ScanRecord"] = relationship("ScanRecord")
