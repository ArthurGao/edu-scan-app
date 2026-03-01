from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Formula(Base):
    __tablename__ = "formulas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    latex: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grade_levels: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(20)), nullable=True
    )
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(100)), nullable=True
    )
    related_ids: Mapped[Optional[List[int]]] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    # embedding column can be added later when pgvector is set up in the database
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
