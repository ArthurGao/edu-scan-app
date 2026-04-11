"""Unit tests for ScanService.rate_solution — feedback push + fail-open."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException


def _make_service(scalar_result):
    """Build a ScanService stub whose db returns the given scalar."""
    from app.services.scan_service import ScanService

    svc = ScanService.__new__(ScanService)
    db = MagicMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none = MagicMock(return_value=scalar_result)
    db.execute = AsyncMock(return_value=exec_result)
    db.commit = AsyncMock()
    svc.db = db
    return svc


def _fake_solution(run_id):
    sol = MagicMock()
    sol.rating = None
    sol.langsmith_run_id = run_id
    return sol


@pytest.mark.asyncio
async def test_rate_solution_persists_rating_and_posts_feedback(monkeypatch):
    sol = _fake_solution("run-xyz")
    svc = _make_service(sol)

    fake_client = MagicMock()
    monkeypatch.setattr(
        "app.services.scan_service.get_langsmith_client",
        lambda: fake_client,
    )

    await svc.rate_solution(
        scan_id=10, user_id=1, rating=5, comment="nailed it",
    )

    assert sol.rating == 5
    svc.db.commit.assert_awaited_once()
    fake_client.create_feedback.assert_called_once()
    kwargs = fake_client.create_feedback.call_args.kwargs
    assert kwargs["run_id"] == "run-xyz"
    assert kwargs["key"] == "user_rating"
    assert kwargs["score"] == 1.0
    assert kwargs["comment"] == "nailed it"
    assert kwargs["value"] == 5


@pytest.mark.asyncio
async def test_rate_solution_without_run_id_still_persists(monkeypatch):
    sol = _fake_solution(None)
    svc = _make_service(sol)

    fake_client = MagicMock()
    monkeypatch.setattr(
        "app.services.scan_service.get_langsmith_client",
        lambda: fake_client,
    )

    await svc.rate_solution(scan_id=10, user_id=1, rating=3)

    assert sol.rating == 3
    fake_client.create_feedback.assert_not_called()


@pytest.mark.asyncio
async def test_rate_solution_fails_open_on_langsmith_error(monkeypatch):
    sol = _fake_solution("run-xyz")
    svc = _make_service(sol)

    fake_client = MagicMock()
    fake_client.create_feedback.side_effect = RuntimeError("LangSmith down")
    monkeypatch.setattr(
        "app.services.scan_service.get_langsmith_client",
        lambda: fake_client,
    )

    # Must not raise — observability never blocks user action.
    await svc.rate_solution(scan_id=10, user_id=1, rating=4)
    assert sol.rating == 4


@pytest.mark.asyncio
async def test_rate_solution_skips_feedback_when_tracing_disabled(monkeypatch):
    sol = _fake_solution("run-xyz")
    svc = _make_service(sol)

    monkeypatch.setattr(
        "app.services.scan_service.get_langsmith_client",
        lambda: None,
    )

    await svc.rate_solution(scan_id=10, user_id=1, rating=4)
    assert sol.rating == 4


@pytest.mark.asyncio
async def test_rate_solution_raises_404_when_not_found(monkeypatch):
    svc = _make_service(None)

    with pytest.raises(HTTPException) as exc:
        await svc.rate_solution(scan_id=10, user_id=1, rating=5)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_rate_solution_validates_range():
    """Rating must be 1-5 — service enforces via ValueError."""
    svc = _make_service(_fake_solution("run-xyz"))
    with pytest.raises(ValueError):
        await svc.rate_solution(scan_id=10, user_id=1, rating=0)
    with pytest.raises(ValueError):
        await svc.rate_solution(scan_id=10, user_id=1, rating=6)
