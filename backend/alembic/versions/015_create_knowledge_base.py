"""Create knowledge_base table

Revision ID: 015_create_knowledge_base
Revises: 013_backfill_curriculum
Create Date: 2026-03-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "015_create_knowledge_base"
down_revision: Union[str, None] = "013_backfill_curriculum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_base",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("grade_levels", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_base_subject", "knowledge_base", ["subject"])

    # Add vector embedding column (requires pgvector extension)
    op.execute("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS embedding vector(1536)")


def downgrade() -> None:
    op.drop_table("knowledge_base")
