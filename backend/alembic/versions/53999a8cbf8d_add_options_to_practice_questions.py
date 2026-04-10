"""add options to practice_questions

Revision ID: 53999a8cbf8d
Revises: 023_add_exam_session_tables
Create Date: 2026-03-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '53999a8cbf8d'
down_revision: Union[str, None] = '023_add_exam_session_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'practice_questions',
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('practice_questions', 'options')
