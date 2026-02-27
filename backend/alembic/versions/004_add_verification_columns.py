"""Add verification and deep evaluation columns to solutions

Revision ID: 004_add_verification_columns
Revises: 003_nullable_image_url
Create Date: 2026-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_add_verification_columns"
down_revision: Union[str, None] = "003_nullable_image_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "solutions",
        sa.Column("verification_status", sa.String(20), nullable=True, server_default="unverified"),
    )
    op.add_column(
        "solutions",
        sa.Column("verification_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "solutions",
        sa.Column("deep_evaluation", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("solutions", "deep_evaluation")
    op.drop_column("solutions", "verification_confidence")
    op.drop_column("solutions", "verification_status")
