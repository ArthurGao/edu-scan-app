"""Unit tests for the _tag_current_run helper in scan_service."""
from unittest.mock import MagicMock

import pytest


def _make_fake_tree():
    tree = MagicMock()
    tree._tags = []
    tree._metadata = {}
    tree.add_tags = lambda t: tree._tags.extend(t)
    tree.add_metadata = lambda m: tree._metadata.update(m)
    return tree


def test_tag_current_run_sets_subject_tier_provider(monkeypatch):
    from app.services import scan_service as mod

    fake = _make_fake_tree()
    monkeypatch.setattr(mod, "get_current_run_tree", lambda: fake)

    mod._tag_current_run(
        subject="math", user_tier="paid", provider="claude", user_id=42,
    )

    assert "subject:math" in fake._tags
    assert "tier:paid" in fake._tags
    assert "provider:claude" in fake._tags
    assert fake._metadata == {"user_id": 42}


def test_tag_current_run_noop_when_no_active_run(monkeypatch):
    """When there is no active LangSmith run, helper must not raise."""
    from app.services import scan_service as mod

    monkeypatch.setattr(mod, "get_current_run_tree", lambda: None)

    # Should simply return None without raising.
    mod._tag_current_run(
        subject="math", user_tier="free", provider=None, user_id=1,
    )


def test_tag_current_run_handles_none_subject_and_provider(monkeypatch):
    """Missing subject/provider should be rendered as 'unknown'/'default'."""
    from app.services import scan_service as mod

    fake = _make_fake_tree()
    monkeypatch.setattr(mod, "get_current_run_tree", lambda: fake)

    mod._tag_current_run(
        subject=None, user_tier="free", provider=None, user_id=7,
    )

    assert "subject:unknown" in fake._tags
    assert "tier:free" in fake._tags
    assert "provider:default" in fake._tags


def test_tag_current_run_swallows_exceptions(monkeypatch):
    """Observability failures must never surface to callers."""
    from app.services import scan_service as mod

    def _boom():
        raise RuntimeError("langsmith exploded")

    monkeypatch.setattr(mod, "get_current_run_tree", _boom)
    mod._tag_current_run(
        subject="math", user_tier="paid", provider="claude", user_id=1,
    )  # must not raise


@pytest.mark.asyncio
async def test_scan_and_solve_calls_tag_helper(monkeypatch):
    """scan_and_solve must invoke _tag_current_run with resolved args."""
    from app.services import scan_service as mod

    captured = {}

    def fake_tag(*, subject, user_tier, provider, user_id):
        captured.update(
            subject=subject, user_tier=user_tier,
            provider=provider, user_id=user_id,
        )

    monkeypatch.setattr(mod, "_tag_current_run", fake_tag)

    svc = mod.ScanService.__new__(mod.ScanService)
    svc.db = MagicMock()
    svc.db.commit = _aw()
    svc.db.flush = _aw()
    svc.db.add = MagicMock()

    fake_graph = MagicMock()
    fake_graph.ainvoke = _aw(return_value={
        "ocr_text": "", "final_solution": {"steps": [], "final_answer": ""},
        "llm_provider": "claude", "llm_model": "claude-sonnet-4",
        "attempt_count": 1, "cache_layer": 1,
    })
    svc._graph = fake_graph
    svc._followup_graph = MagicMock()

    conv = MagicMock()
    conv.add_message = _aw()
    svc._conversation_service = conv

    emb = MagicMock()
    emb.embed_scan_record = _aw()
    svc._embedding_service = emb

    sub_svc_instance = MagicMock()
    sub_svc_instance.get_user_tier = _aw(return_value="paid")
    sub_svc_instance.increment_usage = _aw()
    monkeypatch.setattr(mod, "SubscriptionService", lambda db: sub_svc_instance)

    await svc.scan_and_solve(
        user_id=99, text="2+2=?", subject="math", ai_provider="claude",
    )

    assert captured == {
        "subject": "math",
        "user_tier": "paid",
        "provider": "claude",
        "user_id": 99,
    }


def _aw(return_value=None):
    """Tiny async-mock helper — returns an AsyncMock with the given value."""
    from unittest.mock import AsyncMock
    return AsyncMock(return_value=return_value)
