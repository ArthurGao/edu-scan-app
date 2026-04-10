"""Change embedding dimensions from 1536 to 768 (Google text-embedding-004)

Revision ID: 018_alter_embedding_dims
Revises: 017_add_semantic_cache
Create Date: 2026-03-06

"""
from typing import Sequence, Union

from alembic import op

revision: str = "018_alter_embedding_dims"
down_revision: Union[str, None] = "017_add_semantic_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing index before altering column type
    op.execute("DROP INDEX IF EXISTS ix_knowledge_base_embedding")
    op.execute(
        "ALTER TABLE knowledge_base "
        "ALTER COLUMN embedding TYPE vector(768) USING NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_base_embedding")
    op.execute(
        "ALTER TABLE knowledge_base "
        "ALTER COLUMN embedding TYPE vector(1536) USING NULL"
    )
