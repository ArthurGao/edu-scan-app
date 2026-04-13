"""End-to-end verification that scan.solve runs emit the runtime tags
(`subject:*`, `tier:*`, `provider:*`) that the LangSmith dashboards filter on.

This test doesn't talk to the real LangSmith API — it intercepts the run tree
locally via a fake ``get_current_run_tree`` and verifies that, when invoked
from inside a ``@traceable``-wrapped async function, `_tag_current_run` adds
the expected tags.

If this test passes but the LangSmith UI still shows no tags, the problem is
upstream: either the frontend isn't passing ``subject``/``ai_provider``, or
your backend isn't actually running the `@traceable` code path (e.g. uvicorn
didn't reload after the .env change).
"""
from unittest.mock import MagicMock

import pytest
from langsmith import traceable


def _fake_tree():
    t = MagicMock()
    t._tags = []
    t._metadata = {}
    t.add_tags = lambda tags: t._tags.extend(tags)
    t.add_metadata = lambda md: t._metadata.update(md)
    return t


@pytest.mark.asyncio
async def test_tag_helper_fires_inside_traceable_wrapper(monkeypatch):
    """Simulate a full @traceable async call and verify the helper runs."""
    from app.services import scan_service as mod

    fake = _fake_tree()
    monkeypatch.setattr(mod, "get_current_run_tree", lambda: fake)

    @traceable(run_type="chain", name="test.outer")
    async def outer(subject, user_tier, provider, user_id):
        mod._tag_current_run(
            subject=subject,
            user_tier=user_tier,
            provider=provider,
            user_id=user_id,
        )
        return "ok"

    result = await outer(
        subject="math",
        user_tier="free",
        provider="gemini",
        user_id=10,
    )
    assert result == "ok"
    assert "subject:math" in fake._tags
    assert "tier:free" in fake._tags
    assert "provider:gemini" in fake._tags
    assert fake._metadata == {"user_id": 10}


@pytest.mark.asyncio
async def test_unknown_subject_maps_to_unknown_tag(monkeypatch):
    """When frontend doesn't pass subject, tag should say 'unknown' — the
    LangSmith dashboard can then spot how often that happens."""
    from app.services import scan_service as mod

    fake = _fake_tree()
    monkeypatch.setattr(mod, "get_current_run_tree", lambda: fake)

    mod._tag_current_run(
        subject=None, user_tier="free", provider=None, user_id=1,
    )
    assert "subject:unknown" in fake._tags
    assert "provider:default" in fake._tags
