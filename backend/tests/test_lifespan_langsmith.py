"""Tests for LangSmith init + flush in the FastAPI lifespan."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _patched_engine():
    """Build a MagicMock that stands in for SQLAlchemy's async engine.

    ``engine.begin()`` must yield an async-context-manager whose inner
    ``conn.execute(...)`` is a no-op coroutine — mimics the real API
    without requiring a live database.
    """
    fake_conn = MagicMock()
    fake_conn.execute = AsyncMock()

    class _Ctx:
        async def __aenter__(self):
            return fake_conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_engine = MagicMock()
    fake_engine.begin.return_value = _Ctx()
    return fake_engine


@pytest.mark.asyncio
async def test_lifespan_initializes_client_and_flushes_on_shutdown():
    fake_client = MagicMock()

    with patch("app.main.get_langsmith_client", return_value=fake_client), \
         patch("app.main.engine", _patched_engine()), \
         patch("app.main.settings") as fake_settings:
        fake_settings.rate_limit_enabled = False
        from app.main import app, lifespan

        async with lifespan(app):
            pass

    fake_client.flush.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_handles_missing_client():
    """When tracing is disabled, lifespan must not crash."""
    with patch("app.main.get_langsmith_client", return_value=None), \
         patch("app.main.engine", _patched_engine()), \
         patch("app.main.settings") as fake_settings:
        fake_settings.rate_limit_enabled = False
        from app.main import app, lifespan

        async with lifespan(app):
            pass  # must not raise


@pytest.mark.asyncio
async def test_lifespan_swallows_flush_errors():
    """If LangSmith flush raises, shutdown must still complete."""
    fake_client = MagicMock()
    fake_client.flush.side_effect = RuntimeError("LangSmith down")

    with patch("app.main.get_langsmith_client", return_value=fake_client), \
         patch("app.main.engine", _patched_engine()), \
         patch("app.main.settings") as fake_settings:
        fake_settings.rate_limit_enabled = False
        from app.main import app, lifespan

        async with lifespan(app):
            pass

    fake_client.flush.assert_called_once()
