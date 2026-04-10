from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class SemanticCache(Base):
    __tablename__ = "semantic_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    input_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True) if Vector else None
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    solution_framework: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_hit_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
