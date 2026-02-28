from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionTier(Base):
    __tablename__ = "subscription_tiers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    daily_question_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    allowed_ai_models: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    max_image_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    users: Mapped[List["User"]] = relationship(back_populates="tier")
