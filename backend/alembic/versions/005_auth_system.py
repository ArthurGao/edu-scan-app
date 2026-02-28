"""Auth system - subscription tiers, usage tracking, Clerk integration

Revision ID: 005_auth_system
Revises: 004_add_verification_columns
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "005_auth_system"
down_revision: Union[str, None] = "004_add_verification_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Create subscription_tiers table ---
    subscription_tiers_table = op.create_table(
        "subscription_tiers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("daily_question_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("allowed_ai_models", JSONB(), nullable=False, server_default="[]"),
        sa.Column("features", JSONB(), nullable=False, server_default="{}"),
        sa.Column("max_image_size_mb", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index("ix_subscription_tiers_name", "subscription_tiers", ["name"], unique=True)

    # --- 2. Create daily_usage table ---
    op.create_table(
        "daily_usage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_daily_usage_user_date"),
    )
    op.create_index("ix_daily_usage_user_date", "daily_usage", ["user_id", "usage_date"])

    # --- 3. Create guest_usage table ---
    op.create_table(
        "guest_usage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip_hash", "usage_date", name="uq_guest_usage_ip_date"),
    )

    # --- 4. Create system_settings table ---
    system_settings_table = op.create_table(
        "system_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=True)

    # --- 5. Add columns to users table ---
    op.add_column(
        "users",
        sa.Column("clerk_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)

    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
    )

    op.add_column(
        "users",
        sa.Column("tier_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_tier_id",
        "users",
        "subscription_tiers",
        ["tier_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- 6. Drop password_hash column from users ---
    op.drop_column("users", "password_hash")

    # --- 7. Seed default subscription tiers ---
    op.bulk_insert(
        subscription_tiers_table,
        [
            {
                "name": "free",
                "display_name": "Free",
                "daily_question_limit": 5,
                "allowed_ai_models": ["claude"],
                "features": {
                    "history_access": True,
                    "mistake_book": False,
                    "learning_stats": False,
                    "formula_search": True,
                    "follow_up_questions": True,
                    "max_follow_ups_per_scan": 3,
                    "priority_ai_queue": False,
                    "export_solutions": False,
                },
                "max_image_size_mb": 5,
                "is_default": True,
                "sort_order": 0,
            },
            {
                "name": "basic",
                "display_name": "Basic",
                "daily_question_limit": 20,
                "allowed_ai_models": ["claude", "gpt"],
                "features": {
                    "history_access": True,
                    "mistake_book": True,
                    "learning_stats": False,
                    "formula_search": True,
                    "follow_up_questions": True,
                    "max_follow_ups_per_scan": 5,
                    "priority_ai_queue": False,
                    "export_solutions": False,
                },
                "max_image_size_mb": 10,
                "is_default": False,
                "sort_order": 1,
            },
            {
                "name": "premium",
                "display_name": "Premium",
                "daily_question_limit": 100,
                "allowed_ai_models": ["claude", "gpt", "gemini"],
                "features": {
                    "history_access": True,
                    "mistake_book": True,
                    "learning_stats": True,
                    "formula_search": True,
                    "follow_up_questions": True,
                    "max_follow_ups_per_scan": 10,
                    "priority_ai_queue": False,
                    "export_solutions": True,
                },
                "max_image_size_mb": 20,
                "is_default": False,
                "sort_order": 2,
            },
            {
                "name": "unlimited",
                "display_name": "Unlimited",
                "daily_question_limit": 0,
                "allowed_ai_models": ["claude", "gpt", "gemini"],
                "features": {
                    "history_access": True,
                    "mistake_book": True,
                    "learning_stats": True,
                    "formula_search": True,
                    "follow_up_questions": True,
                    "max_follow_ups_per_scan": 0,
                    "priority_ai_queue": True,
                    "export_solutions": True,
                },
                "max_image_size_mb": 50,
                "is_default": False,
                "sort_order": 3,
            },
        ],
    )

    # --- 8. Seed system settings ---
    op.bulk_insert(
        system_settings_table,
        [
            {
                "key": "guest_daily_limit",
                "value": 3,
                "description": "Maximum number of questions per day for guest users",
            },
            {
                "key": "default_ai_model",
                "value": "claude",
                "description": "Default AI model used for solving problems",
            },
            {
                "key": "maintenance_mode",
                "value": False,
                "description": "Whether the system is in maintenance mode",
            },
            {
                "key": "signup_enabled",
                "value": True,
                "description": "Whether new user registration is enabled",
            },
            {
                "key": "max_upload_size_mb",
                "value": 10,
                "description": "Maximum file upload size in megabytes",
            },
        ],
    )


def downgrade() -> None:
    # --- Reverse 6: Re-add password_hash column ---
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )

    # --- Reverse 5: Drop columns from users ---
    op.drop_constraint("fk_users_tier_id", "users", type_="foreignkey")
    op.drop_column("users", "tier_id")
    op.drop_column("users", "role")
    op.drop_index("ix_users_clerk_id", table_name="users")
    op.drop_column("users", "clerk_id")

    # --- Reverse 4: Drop system_settings table ---
    op.drop_index("ix_system_settings_key", table_name="system_settings")
    op.drop_table("system_settings")

    # --- Reverse 3: Drop guest_usage table ---
    op.drop_table("guest_usage")

    # --- Reverse 2: Drop daily_usage table ---
    op.drop_index("ix_daily_usage_user_date", table_name="daily_usage")
    op.drop_table("daily_usage")

    # --- Reverse 1: Drop subscription_tiers table ---
    op.drop_index("ix_subscription_tiers_name", table_name="subscription_tiers")
    op.drop_table("subscription_tiers")
