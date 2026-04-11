"""Trace-context propagation helpers.

LangChain's tracing runs on contextvars. Spawning work with
``asyncio.create_task`` drops the current context unless the caller
explicitly passes ``context=``. ``spawn_in_current_context`` captures
the current context at spawn time so background work shows up as a
child of the active LangSmith run.

Requires Python 3.11+ (for ``asyncio.Task(..., context=ctx)``).
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
