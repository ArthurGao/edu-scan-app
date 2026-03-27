"""Add source, status, source_question_id, synced_at to practice_questions.

Revision ID: 022_add_q_gen_fields
Revises: 021_add_exam_level
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "022_add_q_gen_fields"
down_revision: Union[str, None] = "021_add_exam_level"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "practice_questions",
        sa.Column("source", sa.String(20), server_default="original", nullable=False),
    )
    op.add_column(
        "practice_questions",
        sa.Column("status", sa.String(20), server_default="approved", nullable=False),
    )
    op.add_column(
        "practice_questions",
        sa.Column(
            "source_question_id",
            sa.Integer(),
            sa.ForeignKey("practice_questions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "practice_questions",
        sa.Column("synced_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_practice_questions_status", "practice_questions", ["status"])
    op.create_index("ix_practice_questions_source", "practice_questions", ["source"])


def downgrade() -> None:
    op.drop_index("ix_practice_questions_source", table_name="practice_questions")
    op.drop_index("ix_practice_questions_status", table_name="practice_questions")
    op.drop_column("practice_questions", "synced_at")
    op.drop_column("practice_questions", "source_question_id")
    op.drop_column("practice_questions", "status")
    op.drop_column("practice_questions", "source")
