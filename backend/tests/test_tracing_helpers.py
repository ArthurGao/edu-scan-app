"""Tests for spawn_in_current_context — trace-context propagation."""
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


@pytest.mark.asyncio
async def test_returns_asyncio_task():
    async def child():
        return 42

    task = spawn_in_current_context(child())
    assert isinstance(task, asyncio.Task)
    assert await task == 42
