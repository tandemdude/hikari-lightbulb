# -*- coding: utf-8 -*-
# Copyright (c) 2023-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

__all__ = ["uniformtrigger", "crontrigger", "TaskExecutionData", "Task"]

import asyncio
import contextlib
import dataclasses
import datetime
import logging
import time
import typing as t

from lightbulb import utils
from lightbulb.internal import di
from lightbulb.internal import types

if t.TYPE_CHECKING:
    from lightbulb import client

TaskFunc: t.TypeAlias = t.Callable[..., t.Awaitable[t.Any]]
Trigger: t.TypeAlias = t.Callable[["TaskExecutionData"], types.MaybeAwaitable[float]]

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True, frozen=True)
class TaskExecutionData:
    invocation_count: int
    last_invocation_length: float
    last_invoked_at: datetime.datetime | None


def uniformtrigger(seconds: int = 0, minutes: int = 0, hours: int = 0, wait_first: bool = True) -> t.Callable[[TaskExecutionData], float]:
    if seconds < 0 or minutes < 0 or hours < 0:
        raise ValueError("seconds, minutes, and hours must be positive")

    if seconds == 0 and minutes == 0 and hours == 0:
        raise ValueError("at least one of seconds, minutes, and hours must not be zero")

    def _trigger(td: TaskExecutionData) -> float:
        if not wait_first and td.invocation_count == 0:
            return 0

        return seconds + minutes * 60 + hours * 3600

    return _trigger


def crontrigger(tab: str) -> t.Callable[[TaskExecutionData], float]:
    try:
        import croniter
    except ImportError:
        raise RuntimeError("crontrigger not available - install Lightbulb with the '[crontrigger]' option to enable")

    cron: croniter.croniter | None = None

    def _trigger(_: TaskExecutionData) -> float:
        nonlocal cron
        if cron is None:
            cron = croniter.croniter(tab, datetime.datetime.now(datetime.timezone.utc))

        diff = cron.get_next(datetime.datetime) - datetime.datetime.now(datetime.timezone.utc)
        return diff.total_seconds()

    return _trigger


class Task:
    __slots__ = [
        "_func",
        "_trigger",
        "_auto_start",
        "_max_failures",
        "_max_invocations",
        "invocation_count",
        "last_invocation_length",
        "last_invoked_at",
        "started",
        "stopped",
        "cancelled",
        "_task",
        "_client",
    ]

    def __init__(
        self,
        func: TaskFunc,
        trigger: Trigger,
        auto_start: bool,
        max_failures: int,
        max_invocations: int,
    ) -> None:
        self._func = func
        self._trigger = trigger
        self._auto_start = auto_start
        self._max_failures = max_failures
        self._max_invocations = max_invocations

        self.invocation_count: int = 0
        self.last_invocation_length: float = -1
        self.last_invoked_at: datetime.datetime | None = None

        self.started = False
        self.stopped = False
        self.cancelled = False

        self._task: asyncio.Task[None] | None = None
        self._client: client.Client | None = None

    @property
    def running(self) -> bool:
        return self.started and not (self.stopped or self.cancelled)

    async def _loop(self) -> None:
        LOGGER.debug("starting task %r", self._func.__name__)

        assert self._client is not None
        self.started = True

        n_failures = 0
        while (
            not self.stopped
            and (self._max_invocations <= 0 or self.invocation_count < self._max_invocations)
            and (self._max_failures <= 0 or n_failures < self._max_failures)
        ):
            to_wait = await utils.maybe_await(
                self._trigger(
                    TaskExecutionData(self.invocation_count, self.last_invocation_length, self.last_invoked_at)
                )
            )
            if to_wait > 0:
                await asyncio.sleep(to_wait)

            LOGGER.debug("invoking task %r", self._func.__name__)

            before, self.last_invoked_at = time.perf_counter(), datetime.datetime.now(datetime.timezone.utc)
            with di.ensure_di_context(self._client.di):
                try:
                    await self._func()
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError):
                        LOGGER.debug("task cancelled")
                        return

                    n_failures += 1
                    LOGGER.warning(
                        "Execution of task %r failed - cancelling after %s more failures",
                        self._func.__name__,
                        self._max_failures - n_failures,
                        exc_info=(type(e), e, e.__traceback__),
                    )

                    if n_failures >= self._max_failures:
                        self.cancelled, self._task = True, None
                        return

            self.last_invocation_length = time.perf_counter() - before
            self.invocation_count += 1

        self.stopped, self._task = True, None
        LOGGER.debug("stopped task %r", self._func.__name__)

    def start(self) -> None:
        if self._client is None or not self._client._started:
            raise RuntimeError("cannot start a task for a non-started Client")

        if self.running:
            return

        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if not self.running:
            return

        self.stopped = True

    def cancel(self) -> None:
        if not self.running:
            return

        assert self._task is not None
        self._task.cancel()
        self._task = None

    async def await_completion(self) -> None:
        if self._task is None:
            return

        with contextlib.suppress(asyncio.CancelledError):
            await self._task
