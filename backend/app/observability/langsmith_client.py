"""Fail-open accessor for the LangSmith ``Client``.

Rules:
- If ``langsmith_tracing`` is False or ``langsmith_api_key`` is empty,
  return ``None``.
- If the ``langsmith`` package is not installed, return ``None``.
- Any exception during construction is logged and becomes ``None``.
- Result is cached per-process until ``reset_client_cache``.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[Any] = None
_checked: bool = False


def _import_client():
    """Isolated so tests can monkeypatch it to simulate ImportError."""
    from langsmith import Client  # type: ignore

    return Client


def reset_client_cache() -> None:
    """Clear cached client — for tests only."""
    global _client, _checked
    _client = None
    _checked = False


def is_tracing_enabled() -> bool:
    return get_langsmith_client() is not None


def get_langsmith_client():
    """Return a cached ``langsmith.Client`` or ``None``.

    Also exports the canonical LangChain tracing env vars so that
    ``ChatAnthropic/ChatOpenAI/...`` auto-trace without further setup.
    """
    global _client, _checked
    if _checked:
        return _client
    _checked = True

    settings = get_settings()
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        _client = None
        return None

    # Export env vars the LangChain callback system reads.
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    if settings.langsmith_endpoint:
        os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith_endpoint)

    try:
        Client = _import_client()
        _client = Client(
            api_key=settings.langsmith_api_key,
            api_url=settings.langsmith_endpoint or None,
        )
        logger.info(
            "LangSmith tracing enabled — project=%s endpoint=%s",
            settings.langsmith_project,
            settings.langsmith_endpoint or "default",
        )
        return _client
    except Exception as e:  # ImportError, network, auth, ...
        logger.warning("LangSmith client unavailable, tracing disabled: %s", e)
        _client = None
        return None
