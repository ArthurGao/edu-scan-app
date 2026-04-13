"""Tests for `_tag_cache_layer`, which emits `cache_layer:L<n>` after solve.

Goal: observability for the 4-layer cache so we can see cache hit rate by
layer in LangSmith dashboards without guessing from Redis/Postgres state.
"""
from unittest.mock import MagicMock

import pytest


def _fake_tree():
    tree = MagicMock()
    tree._tags = []
    tree.add_tags = lambda tags: tree._tags.extend(tags)
    return tree


def test_tag_cache_layer_sets_tag_when_provided(monkeypatch):
    from app.services import scan_service as mod

    fake = _fake_tree()
    monkeypatch.setattr(mod, "get_current_run_tree", lambda: fake)

    mod._tag_cache_layer(4)
    assert "cache_layer:L4" in fake._tags


def test_tag_cache_layer_handles_all_four_layers(monkeypatch):
    from app.services import scan_service as mod

    for layer in (1, 2, 3, 4):
        fake = _fake_tree()
        monkeypatch.setattr(mod, "get_current_run_tree", lambda f=fake: f)
        mod._tag_cache_layer(layer)
        assert f"cache_layer:L{layer}" in fake._tags


def test_tag_cache_layer_noop_when_none(monkeypatch):
    from app.services import scan_service as mod

    fake = _fake_tree()
    monkeypatch.setattr(mod, "get_current_run_tree", lambda: fake)

    mod._tag_cache_layer(None)
    assert fake._tags == []


def test_tag_cache_layer_noop_when_no_active_run(monkeypatch):
    from app.services import scan_service as mod

    monkeypatch.setattr(mod, "get_current_run_tree", lambda: None)
    mod._tag_cache_layer(4)  # must not raise


def test_tag_cache_layer_swallows_exceptions(monkeypatch):
    from app.services import scan_service as mod

    def _boom():
        raise RuntimeError("langsmith broken")

    monkeypatch.setattr(mod, "get_current_run_tree", _boom)
    mod._tag_cache_layer(4)  # must not raise


@pytest.mark.asyncio
async def test_scan_and_solve_calls_cache_layer_tag_after_graph(monkeypatch):
    """scan_and_solve must tag cache_layer after the graph runs, using the
    value from the graph result dict."""
    from unittest.mock import AsyncMock

    from app.services import scan_service as mod

    captured_layers = []

    def fake_tag_cache_layer(layer):
        captured_layers.append(layer)

    monkeypatch.setattr(mod, "_tag_cache_layer", fake_tag_cache_layer)

    svc = mod.ScanService.__new__(mod.ScanService)
    svc.db = MagicMock()
    svc.db.commit = AsyncMock()
    svc.db.flush = AsyncMock()
    svc.db.add = MagicMock()

    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(return_value={
        "ocr_text": "", "final_solution": {"steps": [], "final_answer": ""},
        "llm_provider": "gemini", "llm_model": "gemini-2.5-flash",
        "attempt_count": 1, "cache_layer": 2,  # ← L2 semantic cache hit
    })
    svc._graph = fake_graph
    svc._followup_graph = MagicMock()

    conv = MagicMock()
    conv.add_message = AsyncMock()
    svc._conversation_service = conv

    emb = MagicMock()
    emb.embed_scan_record = AsyncMock()
    svc._embedding_service = emb

    sub = MagicMock()
    sub.get_user_tier = AsyncMock(return_value="free")
    sub.check_usage_limit = AsyncMock(return_value=(True, 10))
    sub.increment_usage = AsyncMock()
    monkeypatch.setattr(mod, "SubscriptionService", lambda db: sub)

    await svc.scan_and_solve(user_id=1, text="test", subject="math")

    assert 2 in captured_layers, (
        "scan_and_solve must call _tag_cache_layer with result['cache_layer']"
    )
