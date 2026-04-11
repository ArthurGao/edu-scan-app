"""Tests for the fail-open LangSmith client accessor."""
from unittest.mock import patch

import pytest

from app.observability.langsmith_client import (
    get_langsmith_client,
    is_tracing_enabled,
    reset_client_cache,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_client_cache()
    yield
    reset_client_cache()


def test_returns_none_when_tracing_disabled():
    with patch("app.observability.langsmith_client.get_settings") as gs:
        gs.return_value.langsmith_tracing = False
        gs.return_value.langsmith_api_key = "ls__x"
        assert get_langsmith_client() is None
        assert is_tracing_enabled() is False


def test_returns_none_when_key_missing_even_if_flag_on():
    with patch("app.observability.langsmith_client.get_settings") as gs:
        gs.return_value.langsmith_tracing = True
        gs.return_value.langsmith_api_key = ""
        assert get_langsmith_client() is None
        assert is_tracing_enabled() is False


def test_returns_client_when_configured():
    with patch("app.observability.langsmith_client.get_settings") as gs:
        gs.return_value.langsmith_tracing = True
        gs.return_value.langsmith_api_key = "ls__fake"
        gs.return_value.langsmith_project = "eduscan-test"
        gs.return_value.langsmith_endpoint = ""
        client = get_langsmith_client()
        assert client is not None
        assert is_tracing_enabled() is True
        # Cached
        assert get_langsmith_client() is client


def test_swallows_import_error_returning_none(monkeypatch):
    import app.observability.langsmith_client as mod

    def _raise():
        raise ImportError("no langsmith")

    monkeypatch.setattr(mod, "_import_client", _raise)
    with patch("app.observability.langsmith_client.get_settings") as gs:
        gs.return_value.langsmith_tracing = True
        gs.return_value.langsmith_api_key = "ls__fake"
        gs.return_value.langsmith_project = "eduscan"
        gs.return_value.langsmith_endpoint = ""
        assert get_langsmith_client() is None
