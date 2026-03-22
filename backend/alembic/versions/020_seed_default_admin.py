"""Seed default admin user for remote deployment.

When deploying to cloud, this migration ensures an admin user exists
so the admin panel can be accessed after first Clerk login.

The admin user is created WITHOUT a clerk_id. On first Clerk login,
security.py matches by email and links the clerk_id automatically.
If clerk_id matching is preferred, update the clerk_id after first login.

Revision ID: 020_seed_default_admin
Revises: 019_add_exam_tables
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "020_seed_default_admin"
down_revision: Union[str, None] = "019_add_exam_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---- CHANGE THIS to your admin email(s) ----
ADMIN_USERS = [
    {
        "email": "arthurgaonz@gmail.com",
        "nickname": "Arthur Gao",
        "role": "admin",
    },
]


def upgrade() -> None:
    users_table = sa.table(
        "users",
        sa.column("email", sa.String),
        sa.column("nickname", sa.String),
        sa.column("role", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    for admin in ADMIN_USERS:
        # Only insert if not already exists (idempotent)
        conn = op.get_bind()
        existing = conn.execute(
            sa.text("SELECT id FROM users WHERE email = :email"),
            {"email": admin["email"]},
        ).fetchone()

        if existing:
            # Update existing user to admin
            conn.execute(
                sa.text("UPDATE users SET role = 'admin' WHERE email = :email"),
                {"email": admin["email"]},
            )
        else:
            # Insert new admin user
            op.bulk_insert(users_table, [{
                "email": admin["email"],
                "nickname": admin["nickname"],
                "role": "admin",
                "is_active": True,
            }])


def downgrade() -> None:
    # Revert admin users back to normal user role (don't delete them)
    conn = op.get_bind()
    for admin in ADMIN_USERS:
        conn.execute(
            sa.text("UPDATE users SET role = 'user' WHERE email = :email"),
            {"email": admin["email"]},
        )
