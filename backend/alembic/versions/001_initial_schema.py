"""Initial schema - users, scans, solutions, formulas, mistakes

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nickname", sa.String(50), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("grade_level", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)

    # Scan records table
    op.create_table(
        "scan_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(50), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_records_user_id", "scan_records", ["user_id"])
    op.create_index("ix_scan_records_created_at", "scan_records", ["created_at"])

    # Solutions table
    op.create_table(
        "solutions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scan_id", sa.BigInteger(), nullable=False),
        sa.Column("ai_provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=True),
        sa.Column("related_formula_ids", postgresql.JSONB(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scan_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solutions_scan_id", "solutions", ["scan_id"])

    # Formulas table
    op.create_table(
        "formulas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("subject", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("latex", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("grade_levels", postgresql.ARRAY(sa.String(20)), nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column("related_ids", postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_formulas_subject", "formulas", ["subject"])
    op.create_index("ix_formulas_category", "formulas", ["category"])
    op.create_index(
        "ix_formulas_keywords",
        "formulas",
        ["keywords"],
        postgresql_using="gin",
    )

    # Mistake books table
    op.create_table(
        "mistake_books",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("scan_id", sa.BigInteger(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("mastered", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("review_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_review_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scan_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mistake_books_user_id", "mistake_books", ["user_id"])
    op.create_index("ix_mistake_books_scan_id", "mistake_books", ["scan_id"])

    # Learning stats table
    op.create_table(
        "learning_stats",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("subject", sa.String(50), nullable=False),
        sa.Column("scan_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("study_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "stat_date", "subject", name="uq_user_date_subject"),
    )
    op.create_index("ix_learning_stats_user_id", "learning_stats", ["user_id"])
    op.create_index("ix_learning_stats_stat_date", "learning_stats", ["stat_date"])


def downgrade() -> None:
    op.drop_table("learning_stats")
    op.drop_table("mistake_books")
    op.drop_table("formulas")
    op.drop_table("solutions")
    op.drop_table("scan_records")
    op.drop_table("users")
