# LangSmith Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add LangSmith as the production observability/monitoring layer for the EduScan backend LLM pipeline, with tracing, tagging, user feedback capture, and safe fail-open behavior when the LangSmith service is unavailable or the API key is absent.

**Architecture:**
The backend is already LangChain + LangGraph based (`app/graph/solve_graph.py`, `app/llm/registry.py`), so LangChain auto-instrumentation gives us the baseline tracing for free via env vars. On top of that we add (1) `@traceable` wrappers at the service-boundary level so each scan is one parent run, (2) metadata/tag propagation via `RunnableConfig`, (3) a `langsmith_run_id` column on `solutions` so user ratings can become LangSmith feedback records, (4) a `POST /scan/{id}/rate` endpoint, (5) background-task trace-context propagation so `asyncio.create_task` children land under their parent run, and (6) graceful flush on shutdown.

**Tech Stack:** LangSmith SDK (`langsmith>=0.2.0`, already in `requirements.txt`), LangChain (already in use), FastAPI, SQLAlchemy 2.0 async, Alembic, pytest + pytest-asyncio + aiosqlite.

---

## Background: Why this design

### What the code actually looks like (CLAUDE.md is stale)

`edu-scan-app/backend/CLAUDE.md` still claims the backend uses LiteLLM and a single `ai_service.py`. **It does not.** The real code:

- Uses **LangChain** `ChatModel` classes (`ChatAnthropic`, `ChatOpenAI`, `ChatGoogleGenerativeAI`, `ChatGroq`) via `app/llm/registry.py:get_llm()`.
- Routes the whole solve pipeline through a **LangGraph** compiled in `app/graph/solve_graph.py`. Node order: `ocr → check_cache → (hit = END | continue → analyze → retrieve → solve → quick_verify → enrich → END)`.
- Has a separate `app/graph/followup_graph.py` for multi-turn chat.
- Has a 4-layer semantic cache (L1 Redis, L2 pgvector, L3 framework, L4 full solve). **Only L4 actually invokes LLMs.** L1-L3 are cheap and should not eat the LangSmith trace budget.
- Spawns background work via `asyncio.create_task()` inside `scan_service.ScanService._persist_and_build_response`: `_run_deep_evaluate_background`, `_write_to_cache`, `_generate_framework_background`, `_generate_practice_background`. `asyncio.create_task` breaks the LangChain trace-context contextvar, so those LLM calls orphan from the parent unless we explicitly propagate.

This plan targets the real architecture. While implementing, **fix `edu-scan-app/backend/CLAUDE.md` in Task 12** to match reality.

### Key discovered facts (verify these hold before starting — files may have drifted since 2026-04-11)

- `langsmith>=0.2.0` is already declared in `edu-scan-app/backend/requirements.txt:42`.
- `langsmith_api_key` and `langsmith_project` are already declared in `edu-scan-app/backend/app/config.py:71-72` (default `""` and `"eduscan"`).
- No endpoint currently writes to `solutions.rating` — grep `app/api/v1` for `rating` returns nothing. So we are creating the rate endpoint from scratch.
- `solutions` table is defined in `edu-scan-app/backend/app/models/solution.py` (22 columns, no `langsmith_run_id` yet).
- Alembic migrations live in `edu-scan-app/backend/alembic/versions/`. Mixed naming: older ones are `NNN_description.py` (e.g. `023_add_exam_session_tables.py`), newer ones are hash-prefixed (e.g. `53999a8cbf8d_add_options_to_practice_questions.py`). Use `alembic revision --autogenerate -m "..."` which produces the hash form.
- Tests use in-memory SQLite via `aiosqlite` set up in `edu-scan-app/backend/tests/conftest.py` with the `get_db` dependency overridden. Pattern: `tests/test_*.py`, async via `pytest-asyncio`.

---

## Design overview

### What LangSmith will see after this plan ships

```
scan.solve  (parent run, tags: subject:math, tier:paid, provider:claude, attempt:0)
├── LangGraph: solve_graph
│   ├── ocr_node (OCR LLM call — Gemini)
│   ├── check_cache_node (no LLM — filter out of trace)
│   ├── analyze_node (fast LLM)
│   ├── retrieve_node (no LLM, pgvector)
│   ├── solve_node (strong LLM — child LLM run with token counts, $)
│   ├── quick_verify_node (fast LLM)
│   └── enrich_node (fast LLM)
├── deep_evaluate (background — propagated via run_tree)
├── framework_generation (background)
└── practice_generation (background)
```

Each parent run gets a `run_id` that is persisted to `solutions.langsmith_run_id`. When the user rates a solution 1-5, we call `Client().create_feedback(run_id=..., key="user_rating", score=rating/5.0)` so the LangSmith dashboard shows rating-by-provider and rating-by-subject.

### Fail-open principle

Every LangSmith interaction must be **fail-open**: if the API is down, the key is missing, or the client call raises, EduScan must continue serving traffic. LangSmith is monitoring; it is not on the critical path. This means:

1. `LANGSMITH_TRACING` defaults to `false` — absent env var = no tracing.
2. The feedback endpoint `try/except`s around `create_feedback` and logs warnings but returns 200.
3. `@traceable` is a no-op when `LANGSMITH_TRACING=false` (the SDK guarantees this).
4. Background task context propagation uses a helper that catches exceptions during context capture/restore.

### What we are NOT doing in this plan

Out of scope (future plans can pick these up):

- Prompt Hub migration of `app/llm/prompts/*.py`
- Offline eval datasets and `langsmith evaluate` CI gating
- LangSmith alerting rule configuration (Slack webhook)
- PII redaction via `LANGSMITH_HIDE_INPUTS` — flagged as a caveat but not configured here
- A pytest regression suite against a golden dataset

This plan delivers the **always-on observability layer** only. Quality gating comes later.

---

## Task breakdown

Tasks are ordered so each is independently testable and commit-able. Tasks 1-3 unlock the baseline; 4-7 are the structured improvements; 8-9 are the feedback loop; 10-12 are operational polish.

Estimated unit of work: each task is one focused ~20-40 minute session.

---

### Task 1: Wire LangSmith env vars into config and `.env.example`

**Goal:** Add the four LangSmith env vars that the SDK looks for, plumb them through `Settings`, and document them in `.env.example`. This task changes no runtime behavior — it only makes configuration available.

**Files:**
- Modify: `edu-scan-app/backend/app/config.py` (around lines 70-72, the "Observability (optional)" block)
- Modify: `edu-scan-app/backend/.env.example` (add new block)

**Step 1: Write the failing test**

Create `edu-scan-app/backend/tests/test_langsmith_config.py`:

```python
import os
from unittest.mock import patch

from app.config import Settings


def test_langsmith_config_defaults_to_disabled():
    """With no env vars set, tracing must be off and endpoint blank."""
    with patch.dict(os.environ, {}, clear=True):
        s = Settings()
        assert s.langsmith_tracing is False
        assert s.langsmith_api_key == ""
        assert s.langsmith_project == "eduscan"
        assert s.langsmith_endpoint == ""
        assert s.langsmith_sampling_rate == 1.0


def test_langsmith_config_reads_env():
    env = {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_API_KEY": "ls__fake",
        "LANGSMITH_PROJECT": "eduscan-test",
        "LANGSMITH_ENDPOINT": "https://eu.api.smith.langchain.com",
        "LANGSMITH_SAMPLING_RATE": "0.25",
    }
    with patch.dict(os.environ, env, clear=True):
        s = Settings()
        assert s.langsmith_tracing is True
        assert s.langsmith_api_key == "ls__fake"
        assert s.langsmith_project == "eduscan-test"
        assert s.langsmith_endpoint == "https://eu.api.smith.langchain.com"
        assert s.langsmith_sampling_rate == 0.25
```

**Step 2: Run it to verify it fails**

```bash
cd edu-scan-app/backend
pytest tests/test_langsmith_config.py -v
```

Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'langsmith_tracing'`.

**Step 3: Add the fields to `Settings`**

In `edu-scan-app/backend/app/config.py`, replace the existing "Observability (optional)" block with:

```python
    # Observability (optional — LangSmith)
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "eduscan"
    langsmith_endpoint: str = ""  # empty = SDK default (US)
    langsmith_sampling_rate: float = 1.0  # 0.0–1.0, honored by our wrapper
```

Pydantic-settings auto-maps `LANGSMITH_TRACING` → `langsmith_tracing` because `case_sensitive=False` is already set on line 11.

**Step 4: Run the test, verify green**

```bash
pytest tests/test_langsmith_config.py -v
```

Expected: 2 passed.

**Step 5: Update `.env.example`**

Append to `edu-scan-app/backend/.env.example`:

```bash
# ── LangSmith Observability (optional) ────────────────────────────────
# When LANGSMITH_TRACING=true and an API key is set, every LangChain
# LLM call is traced automatically. Safe to leave disabled in dev.
# Docs: https://docs.smith.langchain.com/
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=eduscan
# LANGSMITH_ENDPOINT=                   # blank = US region; use https://eu.api.smith.langchain.com for EU
# LANGSMITH_SAMPLING_RATE=1.0           # 0.0–1.0; lower in prod to cap cost
```

If `.env.example` does not exist, create it and add all required vars (inspect `app/config.py` for the full list first — do not guess).

**Step 6: Commit**

```bash
git add edu-scan-app/backend/app/config.py \
        edu-scan-app/backend/.env.example \
        edu-scan-app/backend/tests/test_langsmith_config.py
git commit -m "feat(observability): add LangSmith config settings"
```

---

### Task 2: Add a typed LangSmith client accessor with fail-open behavior

**Goal:** Centralize LangSmith `Client` creation in one module so services never import `langsmith` directly. Returns `None` if tracing is disabled or the SDK is not installed. This is the single seam every other task will call.

**Files:**
- Create: `edu-scan-app/backend/app/observability/__init__.py`
- Create: `edu-scan-app/backend/app/observability/langsmith_client.py`
- Create: `edu-scan-app/backend/tests/test_langsmith_client.py`

**Step 1: Write the failing tests**

`edu-scan-app/backend/tests/test_langsmith_client.py`:

```python
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
    monkeypatch.setattr(mod, "_import_client", lambda: (_ for _ in ()).throw(ImportError("no langsmith")))
    with patch("app.observability.langsmith_client.get_settings") as gs:
        gs.return_value.langsmith_tracing = True
        gs.return_value.langsmith_api_key = "ls__fake"
        assert get_langsmith_client() is None
```

**Step 2: Run, verify they fail with "module not found"**

```bash
pytest tests/test_langsmith_client.py -v
```

**Step 3: Implement `app/observability/__init__.py`**

```python
"""Observability helpers — LangSmith integration.

All LangSmith interaction flows through this package so that services
never import ``langsmith`` directly and fail-open behavior is centralized.
"""
```

**Step 4: Implement `app/observability/langsmith_client.py`**

```python
"""Fail-open accessor for the LangSmith ``Client``.

Rules:
- If ``langsmith_tracing`` is False or ``langsmith_api_key`` is empty,
  return ``None``.
- If the ``langsmith`` package is not installed, return ``None``.
- Any exception during construction is logged and becomes ``None``.
- Result is cached per-process (LRU of size 1) until ``reset_client_cache``.
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
    # Isolated so tests can monkeypatch it to simulate ImportError.
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
    except Exception as e:  # ImportError or network
        logger.warning("LangSmith client unavailable, tracing disabled: %s", e)
        _client = None
        return None
```

**Step 5: Run tests, iterate until green**

```bash
pytest tests/test_langsmith_client.py -v
```

Expected: 4 passed.

**Step 6: Commit**

```bash
git add edu-scan-app/backend/app/observability/ \
        edu-scan-app/backend/tests/test_langsmith_client.py
git commit -m "feat(observability): fail-open LangSmith client accessor"
```

---

### Task 3: Initialize LangSmith in the FastAPI lifespan and flush on shutdown

**Goal:** Call `get_langsmith_client()` once at startup (so env vars are exported before any LangChain code runs) and flush pending traces on shutdown so we don't lose the last batch on SIGTERM.

**Files:**
- Modify: `edu-scan-app/backend/app/main.py` (the `lifespan` function at lines 24-44)

**Step 1: Write the failing test**

Create `edu-scan-app/backend/tests/test_lifespan_langsmith.py`:

```python
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_lifespan_initializes_client_and_flushes_on_shutdown():
    fake_client = MagicMock()
    with patch("app.main.get_langsmith_client", return_value=fake_client):
        from app.main import app
        with TestClient(app):
            pass  # triggers startup + shutdown
        fake_client.flush.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_handles_missing_client():
    """When tracing is disabled, lifespan must not crash."""
    with patch("app.main.get_langsmith_client", return_value=None):
        from app.main import app
        with TestClient(app):
            pass  # must not raise
```

**Step 2: Run, verify failure**

```bash
pytest tests/test_lifespan_langsmith.py -v
```

Expected: `AttributeError: <module 'app.main'> has no attribute 'get_langsmith_client'`.

**Step 3: Modify `app/main.py`**

Add the import at the top:

```python
from app.observability.langsmith_client import get_langsmith_client
```

Modify the `lifespan` function. Replace the existing body with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis

    # LangSmith — initialize cache & export env vars before LangChain first runs.
    ls_client = get_langsmith_client()
    if ls_client is not None:
        logger.info("LangSmith observability active")

    # Startup — fix sequences that may be out of sync with seeded data
    async with engine.begin() as conn:
        await conn.execute(text(
            "SELECT setval('formulas_id_seq', COALESCE((SELECT MAX(id) FROM formulas), 0))"
        ))
    # Initialize Redis for rate limiting
    if settings.rate_limit_enabled:
        try:
            _redis = redis_from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.warning("Rate limiter Redis unavailable, rate limiting disabled: %s", e)
            _redis = None
    yield
    # Shutdown
    if _redis:
        await _redis.aclose()
    if ls_client is not None:
        try:
            ls_client.flush()
        except Exception as e:
            logger.warning("LangSmith flush on shutdown failed: %s", e)
```

**Step 4: Run tests, verify green**

```bash
pytest tests/test_lifespan_langsmith.py -v
```

Expected: 2 passed.

**Step 5: Smoke-run the app**

```bash
LANGSMITH_TRACING=false uvicorn app.main:app --port 8765 &
sleep 2 && curl -s http://localhost:8765/health && kill %1
```

Expected: `{"status":"healthy","app":"EduScan"}` and no tracebacks in the startup log.

**Step 6: Commit**

```bash
git add edu-scan-app/backend/app/main.py \
        edu-scan-app/backend/tests/test_lifespan_langsmith.py
git commit -m "feat(observability): init LangSmith in lifespan + flush on shutdown"
```

---

### Task 4: Wrap `ScanService.scan_and_solve` with `@traceable` as the parent run

**Goal:** Every solve becomes one LangSmith run containing all child LangChain calls, tagged with `subject`, `user_tier`, `provider`, `attempt`. This is the single highest-leverage code change — it turns orphaned LLM calls into a coherent tree.

**Files:**
- Modify: `edu-scan-app/backend/app/services/scan_service.py` (lines 51-102 `scan_and_solve`, and lines 114-196 `scan_and_solve_stream`)
- Create: `edu-scan-app/backend/tests/test_scan_service_traceable.py`

**Step 1: Understand `traceable` first**

Read: `https://docs.smith.langchain.com/observability/how_to_guides/annotate_code#use-traceable--traceable`.

Key API for the async case:

```python
from langsmith import traceable

@traceable(run_type="chain", name="scan.solve", tags=["scan"])
async def scan_and_solve(self, ...): ...
```

When `LANGSMITH_TRACING=false`, `@traceable` is a zero-cost no-op — no import-time side effect, no runtime overhead beyond one env var check.

**Step 2: Write the failing test**

`edu-scan-app/backend/tests/test_scan_service_traceable.py`:

```python
import inspect

from app.services.scan_service import ScanService


def test_scan_and_solve_is_traceable():
    fn = ScanService.scan_and_solve
    # @traceable sets this attribute on the wrapped callable.
    assert getattr(fn, "__langsmith_traceable__", False) is True, (
        "ScanService.scan_and_solve must be wrapped with @traceable"
    )


def test_scan_and_solve_stream_is_traceable():
    fn = ScanService.scan_and_solve_stream
    assert getattr(fn, "__langsmith_traceable__", False) is True
```

> **Note:** The real attribute name may differ across langsmith SDK versions. Verify by running `python -c "from langsmith import traceable; @traceable\nasync def f(): ...\nprint([a for a in dir(f) if 'trace' in a.lower()])"` before finalizing the assertion. Update the test if the attribute name is different. Acceptable alternatives: check `fn.__wrapped__ is not None`, or check `inspect.unwrap(fn) is not fn`.

**Step 3: Run, verify fail**

```bash
pytest tests/test_scan_service_traceable.py -v
```

**Step 4: Wrap the methods**

In `edu-scan-app/backend/app/services/scan_service.py`, add at the top:

```python
from langsmith import traceable
```

Then decorate `scan_and_solve` (line 51) and `scan_and_solve_stream` (line 114):

```python
    @traceable(run_type="chain", name="scan.solve", tags=["scan"])
    async def scan_and_solve(
        self,
        user_id: int,
        image: Optional[UploadFile] = None,
        text: Optional[str] = None,
        subject: Optional[str] = None,
        ai_provider: Optional[str] = None,
        grade_level: Optional[str] = None,
    ) -> ScanResponse:
        ...
```

```python
    @traceable(run_type="chain", name="scan.solve.stream", tags=["scan", "stream"])
    async def scan_and_solve_stream(
        self,
        ...
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

Do not change the method bodies.

**Step 5: Run tests, verify green**

```bash
pytest tests/test_scan_service_traceable.py -v
pytest tests/test_solve_graph.py -v  # regression: existing graph tests still pass
```

Expected: all green.

**Step 6: Commit**

```bash
git add edu-scan-app/backend/app/services/scan_service.py \
        edu-scan-app/backend/tests/test_scan_service_traceable.py
git commit -m "feat(observability): wrap ScanService.solve with @traceable"
```

---

### Task 5: Add dynamic tags & metadata to the scan run

**Goal:** Tags like `subject:math`, `tier:paid`, `provider:claude`, `attempt:0` let us slice dashboards. Static tags on the decorator are not enough — these values are only known at runtime.

**Files:**
- Modify: `edu-scan-app/backend/app/services/scan_service.py` inside `scan_and_solve` (after the tier check, before calling `self._graph.ainvoke`)
- Modify: same file, parallel change in `scan_and_solve_stream`

**Step 1: Write the failing test**

Append to `edu-scan-app/backend/tests/test_scan_service_traceable.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_scan_and_solve_sets_runtime_tags(monkeypatch):
    """Run tags must include subject, tier, provider, and attempt."""
    captured = {}

    def fake_get_current_run_tree():
        tree = MagicMock()
        def add_tags(tags):
            captured.setdefault("tags", []).extend(tags)
        def add_metadata(md):
            captured.setdefault("metadata", {}).update(md)
        tree.add_tags = add_tags
        tree.add_metadata = add_metadata
        return tree

    monkeypatch.setattr(
        "app.services.scan_service.get_current_run_tree",
        fake_get_current_run_tree,
    )

    # Minimal stubs — we only care about the tags being set before ainvoke.
    from app.services import scan_service as mod

    svc = ScanService.__new__(ScanService)
    svc.db = MagicMock()
    svc._graph = MagicMock()
    svc._graph.ainvoke = AsyncMock(return_value={
        "ocr_text": "", "final_solution": {}, "llm_provider": "claude",
        "llm_model": "claude-sonnet-4", "attempt_count": 1, "cache_layer": 1,
    })
    svc._conversation_service = MagicMock()
    svc._conversation_service.add_message = AsyncMock()
    svc._embedding_service = MagicMock()
    svc._embedding_service.embed_scan_record = AsyncMock()

    sub = MagicMock()
    sub.get_user_tier = AsyncMock(return_value="paid")
    sub.increment_usage = AsyncMock()
    monkeypatch.setattr(mod, "SubscriptionService", lambda db: sub)

    svc.db.commit = AsyncMock()
    svc.db.flush = AsyncMock()
    svc.db.add = MagicMock()

    await svc.scan_and_solve(
        user_id=1, text="2+2=?", subject="math", ai_provider="claude",
    )

    assert "subject:math" in captured.get("tags", [])
    assert "tier:paid" in captured.get("tags", [])
    assert "provider:claude" in captured.get("tags", [])
    assert captured.get("metadata", {}).get("user_id") == 1
```

> **Note:** This test is brittle because it reconstructs `ScanService` without `__init__`. If it proves too fragile during implementation, simplify by extracting a small `_tag_current_run(subject, user_tier, provider, user_id)` helper and unit-testing *that* in isolation instead — same goal, fewer mocks.

**Step 2: Run, verify fail**

```bash
pytest tests/test_scan_service_traceable.py::test_scan_and_solve_sets_runtime_tags -v
```

**Step 3: Add tagging helper + call site**

At the top of `scan_service.py`, import:

```python
from langsmith.run_helpers import get_current_run_tree
```

Add a private helper on the module (outside the class, near `_input_hash`):

```python
def _tag_current_run(
    *, subject: Optional[str], user_tier: str,
    provider: Optional[str], user_id: int,
) -> None:
    """Attach business-dimension tags to the active LangSmith run, if any.

    Safe no-op when tracing is disabled (``get_current_run_tree`` returns None).
    Failures are swallowed — observability must never break user requests.
    """
    try:
        tree = get_current_run_tree()
    except Exception:
        return
    if tree is None:
        return
    try:
        tags = [
            f"subject:{subject or 'unknown'}",
            f"tier:{user_tier}",
            f"provider:{provider or 'default'}",
        ]
        tree.add_tags(tags)
        tree.add_metadata({"user_id": user_id})
    except Exception:
        pass
```

Then inside `scan_and_solve`, immediately after resolving `user_tier` (~line 63) and before `self._graph.ainvoke` (~line 83):

```python
        _tag_current_run(
            subject=subject, user_tier=user_tier,
            provider=ai_provider, user_id=user_id,
        )
```

Mirror the same call in `scan_and_solve_stream` at the equivalent location (~line 135).

**Step 4: Run test, verify green**

```bash
pytest tests/test_scan_service_traceable.py -v
```

**Step 5: Commit**

```bash
git add edu-scan-app/backend/app/services/scan_service.py \
        edu-scan-app/backend/tests/test_scan_service_traceable.py
git commit -m "feat(observability): tag scan runs with subject/tier/provider"
```

---

### Task 6: Background task trace-context propagation helper

**Goal:** `asyncio.create_task` drops the LangChain contextvars, so `_run_deep_evaluate_background`, `_write_to_cache`, `_generate_framework_background`, and `_generate_practice_background` all create orphan runs disconnected from their parent scan. Fix with a helper that copies the current `contextvars.Context` into the spawned task.

**Files:**
- Create: `edu-scan-app/backend/app/observability/tracing.py`
- Modify: `edu-scan-app/backend/app/services/scan_service.py` (the four `asyncio.create_task(...)` call sites in `_persist_and_build_response`, roughly lines 289-323)
- Create: `edu-scan-app/backend/tests/test_tracing_helpers.py`

**Step 1: Understand contextvars propagation**

`contextvars.copy_context()` captures the current context; `ctx.run(sync_fn, *args)` re-enters it. For coroutines we need:

```python
import asyncio, contextvars, functools

def spawn_in_current_context(coro_fn, *args, **kwargs):
    ctx = contextvars.copy_context()
    async def _runner():
        # A trick: schedule via loop.call_soon with ctx, then await the inner task
        # Simpler pattern:
        return await coro_fn(*args, **kwargs)
    # Python 3.11+: asyncio.Task accepts a context= kwarg.
    return asyncio.get_running_loop().create_task(_runner(), context=ctx)
```

Python 3.11 added `asyncio.Task(..., context=ctx)`. The backend targets 3.11+ (verify by checking `edu-scan-app/backend/pyproject.toml` or `.python-version`). **If it's on 3.10, escalate — we can't cleanly propagate without upgrading.**

**Step 2: Write the failing test**

`edu-scan-app/backend/tests/test_tracing_helpers.py`:

```python
import asyncio
import contextvars

import pytest

from app.observability.tracing import spawn_in_current_context

_var: contextvars.ContextVar[str] = contextvars.ContextVar("t", default="root")


@pytest.mark.asyncio
async def test_spawned_task_inherits_context():
    _var.set("parent")

    async def child():
        return _var.get()

    task = spawn_in_current_context(child())
    result = await task
    assert result == "parent"


@pytest.mark.asyncio
async def test_spawned_task_isolated_from_later_parent_changes():
    _var.set("parent-at-spawn")

    async def child():
        await asyncio.sleep(0.01)
        return _var.get()

    task = spawn_in_current_context(child())
    _var.set("parent-after-spawn")  # must not leak into child
    result = await task
    assert result == "parent-at-spawn"
```

**Step 3: Run, verify fail**

```bash
pytest tests/test_tracing_helpers.py -v
```

**Step 4: Implement `app/observability/tracing.py`**

```python
"""Trace-context propagation helpers.

LangChain's tracing runs on contextvars. Spawning work with
``asyncio.create_task`` drops the current context by default on
Python <= 3.11.0 and even on later versions when the caller does not
explicitly pass ``context=``. ``spawn_in_current_context`` captures
the current context at spawn time so background work shows up as a
child of the active LangSmith run.
"""
from __future__ import annotations

import asyncio
import contextvars
from typing import Coroutine, TypeVar

T = TypeVar("T")


def spawn_in_current_context(coro: Coroutine[object, object, T]) -> asyncio.Task[T]:
    """Schedule ``coro`` as a task running in a copy of the current context.

    Drop-in replacement for ``asyncio.create_task(coro)`` when you want
    the spawned task to inherit LangChain/LangSmith tracing state.
    """
    ctx = contextvars.copy_context()
    loop = asyncio.get_running_loop()
    return loop.create_task(coro, context=ctx)
```

**Step 5: Swap call sites in `scan_service.py`**

Add import:

```python
from app.observability.tracing import spawn_in_current_context
```

Replace each `asyncio.create_task(self._foo_background(...))` inside `_persist_and_build_response` with `spawn_in_current_context(self._foo_background(...))`. Specifically (around lines 289-323):

- `asyncio.create_task(self._run_deep_evaluate_background(...))` → `spawn_in_current_context(...)`
- `asyncio.create_task(self._write_to_cache(...))` → `spawn_in_current_context(...)`
- `asyncio.create_task(self._generate_framework_background(...))` → `spawn_in_current_context(...)`
- `asyncio.create_task(self._generate_practice_background(...))` → `spawn_in_current_context(...)`

Do **not** change the one at line 513 inside `_generate_practice_background` itself (it is a nested call that should still use plain `asyncio.create_task` if any).

**Step 6: Run tests, verify green**

```bash
pytest tests/test_tracing_helpers.py tests/test_scan_service_traceable.py -v
pytest tests/ -x --timeout=30  # full regression
```

**Step 7: Commit**

```bash
git add edu-scan-app/backend/app/observability/tracing.py \
        edu-scan-app/backend/app/services/scan_service.py \
        edu-scan-app/backend/tests/test_tracing_helpers.py
git commit -m "feat(observability): propagate trace context into bg tasks"
```

---

### Task 7: Add `@traceable` to the followup and grading services

**Goal:** Multi-turn followups and practice grading are the other two major LLM-consuming flows. Wrap them so they also show as coherent runs.

**Files:**
- Modify: `edu-scan-app/backend/app/services/scan_service.py` — `followup` method (line 441)
- Modify: `edu-scan-app/backend/app/services/practice_grading_service.py` — find the primary entry (likely `grade` or `grade_practice`)
- Modify: `edu-scan-app/backend/app/services/grading_service.py` — same (primary public method)

**Step 1: Identify the grading entry points**

```bash
grep -n "async def " edu-scan-app/backend/app/services/practice_grading_service.py
grep -n "async def " edu-scan-app/backend/app/services/grading_service.py
```

Pick the public-facing method in each (the one called from an API route). Do **not** decorate internal helpers — only the outer call.

**Step 2: Decorate**

For each entry point, add above the `async def`:

```python
@traceable(run_type="chain", name="followup.reply", tags=["followup"])
async def followup(self, ...):
```

```python
@traceable(run_type="chain", name="grading.practice", tags=["grading", "practice"])
async def grade(self, ...):
```

```python
@traceable(run_type="chain", name="grading.answer", tags=["grading"])
async def grade_answer(self, ...):
```

Adjust `name=` and `tags=` to match what you actually find.

**Step 3: Write a smoke test**

Create `edu-scan-app/backend/tests/test_service_traceability.py`:

```python
import pytest

from app.services.scan_service import ScanService


@pytest.mark.parametrize("method_name", ["scan_and_solve", "scan_and_solve_stream", "followup"])
def test_scan_service_entry_points_traced(method_name):
    fn = getattr(ScanService, method_name)
    # Flexible check — @traceable wraps, so unwrapping must yield a different object.
    import inspect
    assert inspect.unwrap(fn) is not fn, f"{method_name} must be @traceable"
```

Add analogous parametrized tests for the grading services, using whichever method names you decorated.

**Step 4: Run tests**

```bash
pytest tests/test_service_traceability.py -v
```

**Step 5: Commit**

```bash
git add edu-scan-app/backend/app/services/scan_service.py \
        edu-scan-app/backend/app/services/practice_grading_service.py \
        edu-scan-app/backend/app/services/grading_service.py \
        edu-scan-app/backend/tests/test_service_traceability.py
git commit -m "feat(observability): trace followup + grading flows"
```

---

### Task 8: Add `langsmith_run_id` column to `solutions` and capture it

**Goal:** Persist the parent run id on each `Solution` row so user feedback (Task 9) can reference it later. Feedback can arrive minutes or days after the solve, so we must store the id durably.

**Files:**
- Modify: `edu-scan-app/backend/app/models/solution.py` (after line 41, before `created_at`)
- Create: `edu-scan-app/backend/alembic/versions/<new>_add_langsmith_run_id_to_solutions.py`
- Modify: `edu-scan-app/backend/app/services/scan_service.py` — `_persist_and_build_response` (line 232 where `Solution(...)` is constructed)
- Create: `edu-scan-app/backend/tests/test_solution_run_id.py`

**Step 1: Write the failing test**

`edu-scan-app/backend/tests/test_solution_run_id.py`:

```python
import pytest
from sqlalchemy import select

from app.models.scan_record import ScanRecord
from app.models.solution import Solution


@pytest.mark.asyncio
async def test_solution_persists_langsmith_run_id(db_session):
    scan = ScanRecord(user_id=1, image_url=None, ocr_text="2+2=?")
    db_session.add(scan)
    await db_session.flush()

    sol = Solution(
        scan_id=scan.id,
        ai_provider="claude",
        model="claude-sonnet-4",
        content="4",
        langsmith_run_id="abc-123-def",
    )
    db_session.add(sol)
    await db_session.commit()

    result = await db_session.execute(select(Solution).where(Solution.id == sol.id))
    loaded = result.scalar_one()
    assert loaded.langsmith_run_id == "abc-123-def"


@pytest.mark.asyncio
async def test_solution_run_id_is_nullable(db_session):
    scan = ScanRecord(user_id=1, image_url=None, ocr_text="x")
    db_session.add(scan)
    await db_session.flush()

    sol = Solution(scan_id=scan.id, ai_provider="claude", model="m", content="")
    db_session.add(sol)
    await db_session.commit()  # must not raise
```

(`db_session` fixture comes from existing `conftest.py`. If its name differs, adapt.)

**Step 2: Run, verify fail**

```bash
pytest tests/test_solution_run_id.py -v
```

Expected fail: `AttributeError: 'Solution' has no attribute 'langsmith_run_id'`.

**Step 3: Add column to the model**

In `edu-scan-app/backend/app/models/solution.py`, after the `deep_evaluation` column (line 41), add:

```python
    langsmith_run_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
```

**Step 4: Generate the Alembic migration**

```bash
cd edu-scan-app/backend
alembic revision --autogenerate -m "add langsmith_run_id to solutions"
```

Inspect the generated file under `alembic/versions/`. It should contain:

```python
def upgrade() -> None:
    op.add_column(
        "solutions",
        sa.Column("langsmith_run_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_solutions_langsmith_run_id", "solutions", ["langsmith_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_solutions_langsmith_run_id", table_name="solutions")
    op.drop_column("solutions", "langsmith_run_id")
```

If autogenerate missed the index, add it manually. Do **not** hand-write the migration from scratch — always use autogenerate so the revision chain stays correct.

**Step 5: Capture the run id in `_persist_and_build_response`**

Add near the top of `scan_service.py`:

```python
from langsmith.run_helpers import get_current_run_tree
```

(Already added in Task 5 — skip if present.)

In `_persist_and_build_response` before constructing `Solution(...)`:

```python
        # Capture parent run id so user ratings can later post feedback.
        run_id: Optional[str] = None
        try:
            tree = get_current_run_tree()
            if tree is not None:
                run_id = str(tree.id)
        except Exception:
            run_id = None
```

Then pass `langsmith_run_id=run_id` into the `Solution(...)` constructor.

**Step 6: Run the migration against a test DB and run tests**

```bash
# Tests use in-memory SQLite via conftest, so no manual migration needed for them.
pytest tests/test_solution_run_id.py -v
# Full regression
pytest tests/ -x
```

If the full suite breaks due to the new column not existing in the test schema, check that `conftest.py` creates tables via `Base.metadata.create_all`. If it instead runs alembic migrations, the migration must be fully valid.

**Step 7: Smoke test the migration against the real dev DB**

```bash
alembic upgrade head  # apply
alembic downgrade -1  # verify rollback works
alembic upgrade head  # re-apply
```

**Step 8: Commit**

```bash
git add edu-scan-app/backend/app/models/solution.py \
        edu-scan-app/backend/alembic/versions/*_add_langsmith_run_id_to_solutions.py \
        edu-scan-app/backend/app/services/scan_service.py \
        edu-scan-app/backend/tests/test_solution_run_id.py
git commit -m "feat(observability): persist LangSmith run id on solutions"
```

---

### Task 9: Add `POST /api/v1/scan/{scan_id}/rate` endpoint that pushes feedback

**Goal:** User submits a 1-5 rating on a solution. We store it in `solutions.rating` (existing column) AND forward it to LangSmith as feedback keyed on the `langsmith_run_id`.

**Files:**
- Modify: `edu-scan-app/backend/app/api/v1/scan.py`
- Modify: `edu-scan-app/backend/app/services/scan_service.py` — add `rate_solution` method
- Create: `edu-scan-app/backend/tests/test_rate_endpoint.py`
- Modify: `edu-scan-app/backend/app/schemas/scan.py` — add `RateRequest` schema

**Step 1: Write the failing API test**

`edu-scan-app/backend/tests/test_rate_endpoint.py`:

```python
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_rate_solution_persists_rating_and_posts_feedback(
    authorized_client, solution_factory,
):
    sol = await solution_factory(langsmith_run_id="run-xyz")

    fake_client = MagicMock()
    with patch(
        "app.services.scan_service.get_langsmith_client",
        return_value=fake_client,
    ):
        resp = await authorized_client.post(
            f"/api/v1/scan/{sol.scan_id}/rate",
            json={"rating": 5, "comment": "nailed it"},
        )

    assert resp.status_code == 200
    fake_client.create_feedback.assert_called_once()
    kwargs = fake_client.create_feedback.call_args.kwargs
    assert kwargs["run_id"] == "run-xyz"
    assert kwargs["key"] == "user_rating"
    assert kwargs["score"] == 1.0
    assert kwargs["comment"] == "nailed it"


@pytest.mark.asyncio
async def test_rate_solution_without_run_id_still_persists(
    authorized_client, solution_factory,
):
    sol = await solution_factory(langsmith_run_id=None)
    with patch(
        "app.services.scan_service.get_langsmith_client", return_value=None,
    ):
        resp = await authorized_client.post(
            f"/api/v1/scan/{sol.scan_id}/rate",
            json={"rating": 3},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_solution_swallows_langsmith_errors(
    authorized_client, solution_factory,
):
    sol = await solution_factory(langsmith_run_id="run-xyz")
    fake_client = MagicMock()
    fake_client.create_feedback.side_effect = RuntimeError("LangSmith down")
    with patch(
        "app.services.scan_service.get_langsmith_client",
        return_value=fake_client,
    ):
        resp = await authorized_client.post(
            f"/api/v1/scan/{sol.scan_id}/rate",
            json={"rating": 4},
        )
    # Must still succeed — observability failure ≠ user-facing failure.
    assert resp.status_code == 200
```

> **Fixture note:** `authorized_client` and `solution_factory` may not exist yet. Check `tests/conftest.py`. If they don't:
> 1. Create a minimal `solution_factory` fixture that inserts a `ScanRecord` + `Solution` and returns the `Solution`.
> 2. Use the existing test-client fixture (likely `client` or `async_client`) with a test JWT. If auth is complex, stub `get_current_user` with `app.dependency_overrides`.

**Step 2: Run, verify fail**

```bash
pytest tests/test_rate_endpoint.py -v
```

**Step 3: Define the request schema**

In `edu-scan-app/backend/app/schemas/scan.py` add:

```python
class RateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
```

**Step 4: Implement `ScanService.rate_solution`**

In `scan_service.py`:

```python
from app.observability.langsmith_client import get_langsmith_client
```

```python
    async def rate_solution(
        self, scan_id: int, user_id: int, rating: int, comment: Optional[str] = None,
    ) -> None:
        """Persist user rating on the solution and push it to LangSmith as feedback."""
        result = await self.db.execute(
            select(Solution)
            .join(ScanRecord, Solution.scan_id == ScanRecord.id)
            .where(Solution.scan_id == scan_id, ScanRecord.user_id == user_id)
            .order_by(Solution.created_at.desc())
            .limit(1)
        )
        solution = result.scalar_one_or_none()
        if solution is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="solution_not_found")

        solution.rating = rating
        await self.db.commit()

        # Fail-open feedback push.
        run_id = solution.langsmith_run_id
        if not run_id:
            return
        client = get_langsmith_client()
        if client is None:
            return
        try:
            client.create_feedback(
                run_id=run_id,
                key="user_rating",
                score=rating / 5.0,
                comment=comment,
                value=rating,
            )
        except Exception as e:
            logger.warning(
                "LangSmith create_feedback failed for run %s: %s", run_id, e,
            )
```

**Step 5: Add the route**

In `edu-scan-app/backend/app/api/v1/scan.py` add:

```python
from app.schemas.scan import RateRequest


@router.post("/{scan_id}/rate")
async def rate_solution(
    scan_id: int,
    payload: RateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ScanService(db)
    await service.rate_solution(
        scan_id=scan_id,
        user_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return {"status": "ok"}
```

Register the route only if the scan router is not already auto-included — it already is via `api/v1/router.py`, so just editing the module file is enough.

**Step 6: Rate-limit the new endpoint**

Check `edu-scan-app/backend/app/core/rate_limiter.py` or the config in `config.py` for how endpoints are grouped. The safest default is to reuse the `rate_limit_global_rpm` (60 rpm). If the rate limiter keys on URL prefix, verify the new endpoint falls under a reasonable bucket. If each bucket is a named field on `Settings`, add `rate_limit_rate_rpm: int = 30` and wire it up.

**Step 7: Run tests**

```bash
pytest tests/test_rate_endpoint.py -v
```

**Step 8: Commit**

```bash
git add edu-scan-app/backend/app/api/v1/scan.py \
        edu-scan-app/backend/app/schemas/scan.py \
        edu-scan-app/backend/app/services/scan_service.py \
        edu-scan-app/backend/tests/test_rate_endpoint.py
git commit -m "feat(scan): POST /scan/{id}/rate with LangSmith feedback push"
```

---

### Task 10: Add `@traceable` to the PDF parser service

**Goal:** `pdf_parser_service.parse_exam_pdf` is the biggest non-solve LLM consumer — it runs AI question splitting on every crawled/uploaded exam. A dedicated trace lets us see per-exam parsing cost and debug failures.

**Files:**
- Modify: `edu-scan-app/backend/app/services/pdf_parser_service.py`

**Step 1: Locate the entry points**

```bash
grep -n "async def " edu-scan-app/backend/app/services/pdf_parser_service.py
```

Decorate the public methods only: most likely `parse_exam_pdf` and `parse_schedule_pdf`.

**Step 2: Decorate**

```python
from langsmith import traceable

@traceable(run_type="chain", name="pdf.parse_exam", tags=["pdf", "exam"])
async def parse_exam_pdf(self, pdf_bytes: bytes, ...): ...

@traceable(run_type="chain", name="pdf.parse_schedule", tags=["pdf", "schedule"])
async def parse_schedule_pdf(self, pdf_bytes: bytes, ...): ...
```

**Step 3: Smoke test**

```bash
pytest tests/ -k pdf -v
```

If there are no PDF tests, skip — manual verification via uploading an exam in dev with `LANGSMITH_TRACING=true` is sufficient.

**Step 4: Commit**

```bash
git add edu-scan-app/backend/app/services/pdf_parser_service.py
git commit -m "feat(observability): trace pdf_parser_service entry points"
```

---

### Task 11: Manual end-to-end verification against real LangSmith

**Goal:** Until now everything has been unit-tested against mocks. This task verifies that the whole pipeline actually produces a valid trace tree in the LangSmith UI with all our tags, metadata, and child spans intact.

**This task produces no code — only a checklist run.**

**Steps:**

1. Obtain a dev LangSmith API key from `https://smith.langchain.com/` → Settings → API Keys.
2. Create a fresh project named `eduscan-dev`.
3. Set env in `edu-scan-app/backend/.env`:
   ```bash
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=ls__...
   LANGSMITH_PROJECT=eduscan-dev
   ```
4. Start the backend: `uvicorn app.main:app --reload`. Confirm the startup log contains `LangSmith observability active`.
5. Hit the solve endpoint (authenticated):
   ```bash
   curl -F "image=@tests/test_image.jpg" \
        -F "subject=math" \
        -H "Authorization: Bearer $DEV_TOKEN" \
        http://localhost:8000/api/v1/scan/solve
   ```
6. Open LangSmith → `eduscan-dev` project. Verify you see a run named `scan.solve`. Click into it.
7. **Check run tree contents:**
   - Parent run `scan.solve` has tags `subject:math`, `tier:paid|free`, `provider:<provider>`, and metadata `user_id`.
   - Child runs from the LangGraph nodes appear: ocr, analyze, retrieve, solve, quick_verify, enrich.
   - Each LLM child shows token counts and cost.
8. Capture the `run_id` from the URL (e.g. `/runs/abc-123-def`).
9. Hit the rate endpoint:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -H "Authorization: Bearer $DEV_TOKEN" \
        -d '{"rating": 5, "comment": "test feedback"}' \
        http://localhost:8000/api/v1/scan/<scan_id>/rate
   ```
10. In LangSmith, refresh the run. The Feedback tab should show `user_rating = 1.0` with comment "test feedback".
11. **Background task check:** verify that the run tree includes deep_evaluate/framework/practice children as sibling child runs under the parent (may appear with a few seconds delay).
12. **Fail-open check:** set `LANGSMITH_TRACING=false`, restart, re-run the solve endpoint. It must return 200 and no traces appear in LangSmith. Re-enable.
13. **Shutdown flush check:** with tracing enabled, hit the solve endpoint, then immediately SIGTERM the uvicorn process. Verify all traces appear (no batch loss).

If any step fails, open an issue and link the run URL — do not try to fix by tweaking the plan; fix the underlying cause in the relevant task and re-run this checklist.

**Deliverable:** A comment on the PR describing what you saw, including a LangSmith run URL screenshot.

---

### Task 12: Update docs and fix stale `CLAUDE.md`

**Goal:** Document the new environment variables, the rate endpoint, and fix the two CLAUDE.md files that falsely describe the AI layer as LiteLLM-based.

**Files:**
- Modify: `edu-scan-app/backend/CLAUDE.md` — replace every reference to `ai_service.py` / `LiteLLM` with the actual LangChain + LangGraph architecture. Specifically the `Architecture` tree diagram and the "AI Model Selection" paragraph.
- Modify: `CLAUDE.md` (repo root) — line that says "LiteLLM for multi-model AI support" and the bullet "AI integration via LiteLLM supporting Claude, GPT-4, and Gemini" in the Backend Structure section.
- Modify: `edu-scan-app/docs/LLM_ARCHITECTURE.md` — add a "Observability" section describing LangSmith integration, tags, and the feedback loop.
- Modify: `edu-scan-app/backend/CLAUDE.md` — add a new subsection documenting the rate endpoint and LangSmith vars.

**Step 1: Make edits**

In `edu-scan-app/backend/CLAUDE.md`:
- Remove `ai_service.py` line from the directory tree and replace with `llm/` (containing `registry.py`, `embeddings.py`, `prompts/`).
- Remove the "AI Model Selection" paragraph and replace with a short block pointing to `app/llm/registry.py:get_llm()`.
- Add a new "Observability" subsection after "Testing":

  ```markdown
  ## Observability

  LangSmith traces the LangGraph solve pipeline, grading, and PDF parsing
  when ``LANGSMITH_TRACING=true``. Entry points are wrapped with ``@traceable``
  in ``app/services/scan_service.py`` and friends. See
  ``docs/plans/2026-04-11-langsmith-integration.md`` for the design.

  Required env vars:
  - ``LANGSMITH_TRACING`` (bool, default false)
  - ``LANGSMITH_API_KEY``
  - ``LANGSMITH_PROJECT`` (default ``eduscan``)
  - ``LANGSMITH_ENDPOINT`` (optional, EU region)

  User feedback: ``POST /api/v1/scan/{scan_id}/rate`` accepts a 1-5 rating
  and forwards it to LangSmith as feedback keyed on ``langsmith_run_id``.
  Fails open — LangSmith downtime never blocks the rate request.
  ```

In the repo-root `CLAUDE.md`, fix the two LiteLLM claims.

**Step 2: Commit**

```bash
git add edu-scan-app/backend/CLAUDE.md \
        CLAUDE.md \
        edu-scan-app/docs/LLM_ARCHITECTURE.md
git commit -m "docs: align CLAUDE.md with LangChain+LangGraph reality; document LangSmith"
```

---

## Pre-merge checklist

Before merging the whole branch:

- [ ] `pytest edu-scan-app/backend/tests/ -x` is green.
- [ ] `ruff check edu-scan-app/backend` clean.
- [ ] `mypy edu-scan-app/backend/app` clean (or no new errors if mypy is already not clean).
- [ ] `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` all succeed against a disposable Postgres.
- [ ] Manual verification in Task 11 completed, PR comment with LangSmith run URL posted.
- [ ] `LANGSMITH_TRACING=false` path verified — backend serves traffic identically with tracing off.
- [ ] `.env.example` updated.
- [ ] Stale `ai_service.py`/`LiteLLM` references removed from both `CLAUDE.md`s.

## Caveats the implementer must know

1. **PII:** student photos and OCR text go into LangSmith. For K12 compliance, consider either `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com` or setting `LANGSMITH_HIDE_INPUTS=true` (add as a `Settings` field if adopted). This plan does not configure redaction — flag it in the PR description so the product owner makes a conscious call.
2. **Trace budget:** LangSmith free tier is 5k runs/month. The 4-layer cache already suppresses most solve requests from reaching the LLM, but `pdf.parse_exam` and `grading.practice` are heavy. In production set `LANGSMITH_SAMPLING_RATE=0.2` or add code that sets `LANGSMITH_TRACING=false` for `tier:free` traffic via tag-based sampling. (Out of scope for this plan.)
3. **`asyncio.create_task` context propagation** relies on Python 3.11+. Verify `backend` runs on 3.11+ before starting Task 6. If on 3.10, escalate.
4. **Alembic autogenerate diff** — after Task 8's autogenerate, review the revision file carefully. Autogenerate sometimes picks up unrelated schema drift; delete any additions that are not the `langsmith_run_id` column and its index.
5. **Do not import `langsmith` outside `app/observability/`.** All interactions route through the accessor so that removing LangSmith in the future is a one-directory change.

## Related skills to invoke while executing

- Before each task: `superpowers:test-driven-development`
- Before committing: `superpowers:verification-before-completion`
- For any confusing test failure: `superpowers:systematic-debugging`
- For the final PR: `superpowers:requesting-code-review`
