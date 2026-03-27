"""Add level column to exam_papers.

Revision ID: 021_add_exam_level
Revises: 020_seed_default_admin
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "021_add_exam_level"
down_revision: Union[str, None] = "020_seed_default_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exam_papers", sa.Column("level", sa.Integer(), nullable=False, server_default="1"))
    op.create_index("ix_exam_papers_level", "exam_papers", ["level"])


def downgrade() -> None:
    op.drop_index("ix_exam_papers_level", table_name="exam_papers")
    op.drop_column("exam_papers", "level")
