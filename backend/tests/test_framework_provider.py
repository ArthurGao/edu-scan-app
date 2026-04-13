"""Regression test for framework-generation provider consistency.

Before the fix: `_generate_framework_background` hard-coded `get_llm("fast")`
which defaults to the configured `default_ai_provider` (usually Claude) —
so a free-tier user whose solve ran on Gemini would still burn Claude Haiku
tokens on the background framework step.

After the fix: the caller passes the *actual* solve provider through, so
framework-gen runs on the same provider as solve.
"""
import inspect

from app.services.scan_service import ScanService


def test_generate_framework_background_accepts_provider_kwarg():
    """The function must accept a `provider` kwarg so callers can pin it."""
    sig = inspect.signature(ScanService._generate_framework_background)
    assert "provider" in sig.parameters, (
        "_generate_framework_background must accept a `provider` kwarg so "
        "callers can pass the same provider that was used for solve"
    )
    # Must default to None so callers that don't know the provider still work
    assert sig.parameters["provider"].default is None


def test_persist_and_build_response_forwards_llm_provider(monkeypatch):
    """`_persist_and_build_response` must forward `result['llm_provider']`
    to `_generate_framework_background` when it spawns the background task."""
    # Read the source of _persist_and_build_response and verify that the
    # call to _generate_framework_background references llm_provider.
    src = inspect.getsource(ScanService._persist_and_build_response)
    # The background spawn block must mention llm_provider near the framework call.
    idx = src.find("_generate_framework_background")
    assert idx != -1, "framework background call not found"
    # Look at 500 chars of context around the call site
    window = src[max(0, idx - 100): idx + 500]
    assert "llm_provider" in window, (
        "_persist_and_build_response must pass result['llm_provider'] to "
        "_generate_framework_background so the provider stays consistent "
        "with the solve provider"
    )
