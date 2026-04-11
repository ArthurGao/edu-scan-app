"""add langsmith_run_id to solutions

Revision ID: a7c4f9e2b1d0
Revises: 53999a8cbf8d
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c4f9e2b1d0'
down_revision: Union[str, None] = '53999a8cbf8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'solutions',
        sa.Column('langsmith_run_id', sa.String(length=64), nullable=True),
    )
    op.create_index(
        'ix_solutions_langsmith_run_id',
        'solutions',
        ['langsmith_run_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_solutions_langsmith_run_id', table_name='solutions')
    op.drop_column('solutions', 'langsmith_run_id')
