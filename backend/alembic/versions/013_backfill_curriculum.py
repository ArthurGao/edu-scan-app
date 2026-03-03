"""Backfill curriculum tags on original 30 formulas

Revision ID: 013_backfill_curriculum
Revises: 012_seed_ncea_chemistry
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_backfill_curriculum"
down_revision: Union[str, None] = "012_seed_ncea_chemistry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Math formulas (IDs 1-12) — most appear across both curricula
    # 1: Quadratic Formula — IGCSE, AS, NCEA L1, L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-1', 'ncea-2'] WHERE id = 1")
    # 2: Pythagorean Theorem — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 2")
    # 3: Slope Formula — IGCSE, NCEA L1, L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1', 'ncea-2'] WHERE id = 3")
    # 4: Distance Formula — IGCSE, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-2'] WHERE id = 4")
    # 5: Area of Circle — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 5")
    # 6: Circumference — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 6")
    # 7: Area of Triangle — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 7")
    # 8: Linear Equation — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 8")
    # 9: Binomial Theorem — AS, A2, NCEA L3
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-as', 'cambridge-a2', 'ncea-3'] WHERE id = 9")
    # 10: Logarithm Product Rule — AS, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-as', 'ncea-2'] WHERE id = 10")
    # 11: Sine Rule — IGCSE, AS, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-2'] WHERE id = 11")
    # 12: Cosine Rule — IGCSE, AS, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-2'] WHERE id = 12")

    # Physics formulas (IDs 13-22) — shared across both curricula
    # 13: Newton's Second Law F=ma — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-1'] WHERE id = 13")
    # 14: Kinetic Energy — IGCSE, AS, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-1'] WHERE id = 14")
    # 15: Potential Energy — IGCSE, AS, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-1'] WHERE id = 15")
    # 16: Ohm's Law — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 16")
    # 17: Speed — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 17")
    # 18: Acceleration — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 18")
    # 19: Work — IGCSE, AS, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-1'] WHERE id = 19")
    # 20: Power — IGCSE, AS, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-1'] WHERE id = 20")
    # 21: Momentum — AS, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-as', 'ncea-2'] WHERE id = 21")
    # 22: Gravitational Force — A2, NCEA L3
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-a2', 'ncea-3'] WHERE id = 22")

    # Chemistry formulas (IDs 23-30) — shared across both curricula
    # 23: Ideal Gas Law — AS, A2, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-as', 'cambridge-a2', 'ncea-2'] WHERE id = 23")
    # 24: Density — IGCSE, NCEA L1
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'ncea-1'] WHERE id = 24")
    # 25: Molarity — IGCSE, AS, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-2'] WHERE id = 25")
    # 26: pH — AS, NCEA L1, L3
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-as', 'cambridge-a2', 'ncea-1', 'ncea-3'] WHERE id = 26")
    # 27: Dilution — IGCSE, AS, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-2'] WHERE id = 27")
    # 28: Avogadro's Number — IGCSE, AS, NCEA L2
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-igcse', 'cambridge-as', 'ncea-2'] WHERE id = 28")
    # 29: Reaction Rate — AS, A2, NCEA L3
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-as', 'cambridge-a2', 'ncea-3'] WHERE id = 29")
    # 30: Enthalpy — AS, A2, NCEA L2, L3
    op.execute("UPDATE formulas SET curriculum = ARRAY['cambridge-as', 'cambridge-a2', 'ncea-2', 'ncea-3'] WHERE id = 30")


def downgrade() -> None:
    op.execute("UPDATE formulas SET curriculum = ARRAY['generic'] WHERE id <= 30")
