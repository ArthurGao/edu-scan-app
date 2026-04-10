from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    pass


class ExamPaper(Base):
    __tablename__ = "exam_papers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    subject: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[int] = mapped_column(Integer, default=1, index=True)  # NCEA Level 1, 2, 3
    exam_code: Mapped[str] = mapped_column(String(50))
    paper_type: Mapped[str] = mapped_column(String(20))  # "exam" | "schedule"
    language: Mapped[str] = mapped_column(String(50), default="english")
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    questions: Mapped[List["PracticeQuestion"]] = relationship(
        "PracticeQuestion", back_populates="exam_paper", cascade="all, delete-orphan"
    )


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_paper_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exam_papers.id", ondelete="CASCADE"), index=True, nullable=True
    )
    question_number: Mapped[str] = mapped_column(String(20))  # "ONE", "TWO"
    sub_question: Mapped[str] = mapped_column(String(10))  # "a", "b", "c"
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # "numeric" | "multichoice" | "explanation"
    correct_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accepted_answers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    answer_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    marks: Mapped[Optional[str]] = mapped_column(
        String(5), nullable=True
    )  # "A" or "H"
    outcome: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    options: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # ["option A text", "option B text", ...] for multichoice
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    image_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    # AI generation fields
    source: Mapped[str] = mapped_column(
        String(20), default="original", server_default="original"
    )  # "original" | "ai_generated"
    status: Mapped[str] = mapped_column(
        String(20), default="approved", server_default="approved"
    )  # "draft" | "approved" | "rejected"
    source_question_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("practice_questions.id", ondelete="SET NULL"), nullable=True
    )  # ID of original question this was generated from
    synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )  # Timestamp of last sync to remote Neon

    # Practice generation fields
    visibility: Mapped[str] = mapped_column(
        String(20), default="private", server_default="private"
    )  # "private" | "public"
    generated_for_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    difficulty_offset: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )  # 0=same, 1=harder, 2=hardest
    usage_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    correct_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auto_promoted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    source_scan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("scan_records.id", ondelete="SET NULL"), nullable=True
    )
    knowledge_points: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    problem_type_tag: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # "quadratic_equation", etc.
    difficulty: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # "easy" | "medium" | "hard" | "very_hard"

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    exam_paper: Mapped["ExamPaper"] = relationship(
        "ExamPaper", back_populates="questions"
    )
    source_question: Mapped[Optional["PracticeQuestion"]] = relationship(
        "PracticeQuestion", remote_side="PracticeQuestion.id", foreign_keys=[source_question_id]
    )

    __table_args__ = (
        Index("ix_practice_questions_status", "status"),
        Index("ix_practice_questions_source", "source"),
        Index("ix_practice_questions_visibility", "visibility"),
        Index("ix_practice_questions_source_scan", "source_scan_id"),
        Index("ix_practice_questions_generated_for", "generated_for_user_id"),
    )
