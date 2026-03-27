"""Add exam_sessions and exam_answers tables.

Revision ID: 023_add_exam_session_tables
Revises: 022_add_q_gen_fields
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "023_add_exam_session_tables"
down_revision: Union[str, None] = "022_add_q_gen_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_paper_id",
            sa.Integer(),
            sa.ForeignKey("exam_papers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_type", sa.String(20), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="in_progress", nullable=False),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("graded_at", sa.DateTime(), nullable=True),
        sa.Column("filter_criteria", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_exam_sessions_user_status", "exam_sessions", ["user_id", "status"]
    )

    op.create_table(
        "exam_answers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("exam_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("practice_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("student_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Float(), default=1.0),
        sa.Column("grading_method", sa.String(20), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("graded_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "session_id", "question_id", name="uq_exam_answer_session_question"
        ),
    )
    op.create_index("ix_exam_answers_session", "exam_answers", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_answers_session", table_name="exam_answers")
    op.drop_table("exam_answers")
    op.drop_index("ix_exam_sessions_user_status", table_name="exam_sessions")
    op.drop_table("exam_sessions")
