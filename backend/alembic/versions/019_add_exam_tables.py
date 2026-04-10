"""Add exam_papers and practice_questions tables

Revision ID: 019_add_exam_tables
Revises: 018_alter_embedding_dims
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "019_add_exam_tables"
down_revision: Union[str, None] = "018_alter_embedding_dims"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_papers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(50), nullable=False),
        sa.Column("exam_code", sa.String(50), nullable=False),
        sa.Column("paper_type", sa.String(20), nullable=False),
        sa.Column("language", sa.String(50), nullable=False, server_default="english"),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exam_papers_year", "exam_papers", ["year"])
    op.create_index("ix_exam_papers_subject", "exam_papers", ["subject"])

    op.create_table(
        "practice_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exam_paper_id", sa.Integer(), nullable=False),
        sa.Column("question_number", sa.String(20), nullable=False),
        sa.Column("sub_question", sa.String(10), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("accepted_answers", postgresql.JSONB(), nullable=True),
        sa.Column("answer_explanation", sa.Text(), nullable=True),
        sa.Column("marks", sa.String(5), nullable=True),
        sa.Column("outcome", sa.Integer(), nullable=True),
        sa.Column("has_image", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["exam_paper_id"],
            ["exam_papers.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_practice_questions_exam_paper_id",
        "practice_questions",
        ["exam_paper_id"],
    )


def downgrade() -> None:
    op.drop_table("practice_questions")
    op.drop_table("exam_papers")
