"""Make image_url nullable and add missing scan_records columns

Revision ID: 003_nullable_image_url
Revises: 002_seed_formulas
Create Date: 2026-02-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_nullable_image_url"
down_revision: Union[str, None] = "002_seed_formulas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension is available (Neon has it built-in)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Make image_url nullable for text-only input
    op.alter_column(
        "scan_records",
        "image_url",
        existing_type=sa.String(500),
        nullable=True,
    )

    # Add columns that exist in the model but were missing from migration 001
    op.add_column(
        "scan_records",
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "scan_records",
        sa.Column("problem_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "scan_records",
        sa.Column("knowledge_points", postgresql.JSONB(), nullable=True),
    )
    # Use raw SQL for vector type since alembic doesn't have native vector support
    op.execute("ALTER TABLE scan_records ADD COLUMN IF NOT EXISTS embedding vector(1536)")

    # Create conversation_messages table (missing from migration 001)
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scan_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scan_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_messages_scan_id", "conversation_messages", ["scan_id"])

    # Add missing columns to solutions table
    op.add_column(
        "solutions",
        sa.Column("final_answer", sa.Text(), nullable=True),
    )
    op.add_column(
        "solutions",
        sa.Column("knowledge_points", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "solutions",
        sa.Column("quality_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "solutions",
        sa.Column("attempt_number", sa.Integer(), nullable=True),
    )

    # Add missing columns to mistake_books table
    op.add_column(
        "mistake_books",
        sa.Column("subject", sa.String(50), nullable=True),
    )
    op.add_column(
        "mistake_books",
        sa.Column("tags", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "mistake_books",
        sa.Column("mastery_level", sa.SmallInteger(), server_default="0"),
    )
    op.add_column(
        "mistake_books",
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mistake_books", "last_reviewed_at")
    op.drop_column("mistake_books", "mastery_level")
    op.drop_column("mistake_books", "tags")
    op.drop_column("mistake_books", "subject")
    op.drop_index("ix_conversation_messages_scan_id", "conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_column("solutions", "attempt_number")
    op.drop_column("solutions", "quality_score")
    op.drop_column("solutions", "knowledge_points")
    op.drop_column("solutions", "final_answer")
    op.drop_column("scan_records", "embedding")
    op.drop_column("scan_records", "knowledge_points")
    op.drop_column("scan_records", "problem_type")
    op.drop_column("scan_records", "ocr_confidence")
    op.execute("UPDATE scan_records SET image_url = '' WHERE image_url IS NULL")
    op.alter_column(
        "scan_records",
        "image_url",
        existing_type=sa.String(500),
        nullable=False,
    )
