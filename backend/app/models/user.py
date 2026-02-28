from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.mistake_book import MistakeBook
    from app.models.scan_record import ScanRecord
    from app.models.subscription_tier import SubscriptionTier


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    clerk_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    grade_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    tier_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("subscription_tiers.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tier: Mapped[Optional["SubscriptionTier"]] = relationship(back_populates="users")
    scan_records: Mapped[List["ScanRecord"]] = relationship(
        "ScanRecord", back_populates="user", cascade="all, delete-orphan"
    )
    mistake_books: Mapped[List["MistakeBook"]] = relationship(
        "MistakeBook", back_populates="user", cascade="all, delete-orphan"
    )
