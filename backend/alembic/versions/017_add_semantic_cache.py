"""Add semantic_cache table for LLM response caching

Revision ID: 017_add_semantic_cache
Revises: 016_seed_problems_gemini
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op

revision: str = "017_add_semantic_cache"
down_revision: Union[str, None] = "016_seed_problems_gemini"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cache (
            id          SERIAL PRIMARY KEY,
            input_hash  VARCHAR(64) NOT NULL,
            input_text  TEXT NOT NULL,
            embedding   vector(768),
            response    JSONB NOT NULL,
            solution_framework JSONB,
            model_used  VARCHAR(50),
            hit_count   INTEGER NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ DEFAULT now(),
            last_hit_at TIMESTAMPTZ,
            CONSTRAINT uq_semantic_cache_hash UNIQUE (input_hash)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_cache_hash
        ON semantic_cache (input_hash)
    """)

    # Vector index — add after table has 100+ rows for best performance.
    # Uses ivfflat with lists=1 so it works on empty/small tables.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding
        ON semantic_cache
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 1)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS semantic_cache")
