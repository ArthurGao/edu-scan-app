"""Tests for the langsmith_run_id column on the Solution model.

The existing db_session fixture doesn't support the full schema on SQLite
(Postgres ARRAY/JSONB types), so these assert the column declaration at
the SQLAlchemy level. The actual round-trip is verified by running the
alembic migration against real Postgres.
"""
from sqlalchemy import String

from app.models.solution import Solution


def test_solution_has_langsmith_run_id_column():
    col = Solution.__table__.c.get("langsmith_run_id")
    assert col is not None, "solutions.langsmith_run_id column must exist"
    assert col.nullable is True
    assert isinstance(col.type, String)
    assert col.type.length == 64
    assert col.index is True, "langsmith_run_id should be indexed"


def test_solution_can_construct_with_run_id():
    """Verify the ORM attribute accepts a string without raising."""
    sol = Solution(
        scan_id=1,
        ai_provider="claude",
        model="claude-sonnet-4",
        content="4",
        langsmith_run_id="abc-123-def",
    )
    assert sol.langsmith_run_id == "abc-123-def"


def test_solution_run_id_defaults_to_none():
    sol = Solution(scan_id=1, ai_provider="claude", model="m", content="")
    assert sol.langsmith_run_id is None
