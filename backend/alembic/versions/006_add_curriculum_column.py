"""Add curriculum column to formulas

Revision ID: 006_add_curriculum_column
Revises: 005_auth_system
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_add_curriculum_column"
down_revision: Union[str, None] = "005_auth_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "formulas",
        sa.Column("curriculum", postgresql.ARRAY(sa.String(50)), nullable=True),
    )
    op.create_index(
        "ix_formulas_curriculum",
        "formulas",
        ["curriculum"],
        postgresql_using="gin",
    )
    # Backfill existing formulas as generic
    op.execute("UPDATE formulas SET curriculum = ARRAY['generic'] WHERE curriculum IS NULL")


def downgrade() -> None:
    op.drop_index("ix_formulas_curriculum")
    op.drop_column("formulas", "curriculum")
