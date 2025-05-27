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
"""
This module implements simple asynchronous tasks that run alongside the Lightbulb client.

----

Usage Guide
-----------

Creating Tasks
^^^^^^^^^^^^^^

Tasks can be created using one of the provided decorators:

- :meth:`@client.task() <lightbulb.client.Client.task>`
- :meth:`@loader.task() <lightbulb.loaders.Loader.task>`

When creating a task, you must pass a trigger callable that will be used to know when and how often the task
should be invoked.

Built-in Triggers
^^^^^^^^^^^^^^^^^

Lightbulb has two built-in triggers that you can use for your own tasks. These are
:obj:`~lightbulb.tasks.uniformtrigger` and :obj:`~lightbulb.tasks.crontrigger`.

**uniformtrigger**

When used, this trigger will invoke the task at the given uniform interval. I.e. if you set the interval to
10 seconds, the task will be invoked every 10 seconds. The countdown before each invocation will start once
the previous invocation has finished.

**crontrigger**

.. important::
    To use this trigger you need to install Lightbulb with the optional dependency ``[crontrigger]``

When used, this trigger invokes the task following the given crontab. For example, you could use this trigger
to schedule the task to run every day at 10am. This trigger's schedule is always calculated from UTC.

Custom Triggers
^^^^^^^^^^^^^^^

Creating your own custom trigger is easy. A trigger is any callable that takes a single parameter - this will be
an instance of :obj:`~lightbulb.tasks.TaskExecutionData` - and returns a float. This will be called after every
invocation of the task in order to calculate how much time to wait until the next task invocation.

The task execution data object contains some information you can use if you wish to set next the interval based on
when the task was last invoked, or how long the last invocation took.

Running Tasks
^^^^^^^^^^^^^

Tasks registered to the client will be run automatically once the client's ``start`` method has been called. Any
tasks registered after the client has already been started will be run immediately. If, when creating your task,
you pass ``auto_start=False``, then you will instead need to call the task's start method manually.

If the task is registered to a loader, once the loader is removed from the client the task will be cancelled.

----
"""

from __future__ import annotations

__all__ = ["Task", "TaskExecutionData", "crontrigger", "uniformtrigger"]

import asyncio
import contextlib
import dataclasses
import datetime
import logging
import time
import typing as t
from collections.abc import Awaitable
from collections.abc import Callable

from lightbulb import di
from lightbulb import utils
from lightbulb.internal import types

if t.TYPE_CHECKING:
    from lightbulb import client

TaskFunc: t.TypeAlias = Callable[..., Awaitable[t.Any]]
Trigger: t.TypeAlias = Callable[["TaskExecutionData"], types.MaybeAwaitable[float]]

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True, frozen=True)
class TaskExecutionData:
    """Dataclass representing the data passed to a trigger function."""

    invocation_count: int
    """The number of times the task has been invoked so far."""
    last_invocation_length: float
    """The length of the last invocation of the task. Will be ``-1`` if the task has not been invoked yet."""
    last_invoked_at: datetime.datetime | None
    """The time (UTC) of the last invocation of the task or :obj:`None` if the task has not been invoked."""


def uniformtrigger(
    seconds: int = 0, minutes: int = 0, hours: int = 0, wait_first: bool = True
) -> Callable[[TaskExecutionData], float]:
    """
    Generates a trigger function that returns uniform intervals from the given arguments. At least one
    of ``seconds``, ``minutes``, and ``hours`` must be specified. If multiple are specified then the
    intervals will be combined. I.e. if ``hours`` is ``1`` AND ``seconds`` is ``5``, then the generated interval
    will be ``3605`` seconds (1 hour 5 seconds).

    Args:
        seconds: The number of seconds for the interval.
        minutes: The number of minutes for the interval.
        hours: The number of hours for the interval.
        wait_first: Whether the first invocation of the task should wait for the interval to elapse. Defaults to
            :obj:`True`.

    Returns:
        The generated trigger function.

    Raises:
        :obj:`ValueError`: When all interval arguments are 0, or any interval argument is negative.

    Example:

        .. code-block:: python

            @client.task(lightbulb.uniformtrigger(minutes=1))
            async def print_hi() -> None:
                print("HI")
    """
    if seconds < 0 or minutes < 0 or hours < 0:
        raise ValueError("seconds, minutes, and hours must be positive")

    if seconds == 0 and minutes == 0 and hours == 0:
        raise ValueError("at least one of seconds, minutes, and hours must not be zero")

    def _trigger(td: TaskExecutionData) -> float:
        if not wait_first and td.invocation_count == 0:
            return 0

        return seconds + minutes * 60 + hours * 3600

    return _trigger


def crontrigger(tab: str) -> Callable[[TaskExecutionData], float]:
    """
    Generates a crontab-based task trigger. Tasks will be run dependent on the given crontab. You can use a tool
    such as `crontab.guru <https://crontab.guru/>`_ to aid in creating an appropriate crontab.

    Args:
        tab: The crontab to use to schedule task execution.

    Returns:
        The generated trigger function.

    Note:
        The crontab is **always** evaluated using UTC time.

    Warning:
        This trigger is not available unless you have the ``croniter`` requirement installed. For convenience, you
        can install this using the '[crontrigger]' option when installing Lightbulb.

        E.g. ``pip install hikari-lightbulb[crontrigger]``

    Warning:
        If the task execution takes longer than the interval specified by the crontab, the next execution will
        take place at the next suitable time after the execution completed. For example, if you specify the task
        should run at every 5th minute, but the execution at the 0th minute takes 6 minutes - the task would next
        be executed at the 10th minute instead of the 5th minute.

    Example:

        .. code-block:: python

            # Crontab '* * * * *' means 'run at every minute'
            @client.task(lightbulb.crontrigger("* * * * *"))
            async def print_hi() -> None:
                print("HI")
    """
    try:
        import croniter
    except ImportError:
        raise RuntimeError("crontrigger not available - install Lightbulb with the '[crontrigger]' option to enable")

    cron: croniter.croniter = croniter.croniter(tab)

    def _trigger(_: TaskExecutionData) -> float:
        diff = cron.get_next(datetime.datetime, now := datetime.datetime.now(datetime.timezone.utc)) - now
        return diff.total_seconds()

    return _trigger


class Task:
    """
    Class representing an asynchronous repeating task.

    Args:
        func: The function to execute. Dependency injection will be enabled for it once the task is created.
        trigger: The trigger function to use to resolve the interval between task executions.
        auto_start: Whether the task should be started automatically. This means that if the task is added to
            the client upon the client being started, the task will also be started; it will also be started
            if being added to an already-started client.
        max_failures: The maximum number of failed attempts to execute the task before it is cancelled.
            Setting this to a negative number will prevent the task from being cancelled, regardless of
            how often the task fails.
        max_invocations: The maximum number of times the task can be invoked before being stopped.
            Setting this to a negative number will disable this behaviour, allowing unlimited invocations.
    """

    __slots__ = [
        "_auto_start",
        "_client",
        "_func",
        "_max_failures",
        "_max_invocations",
        "_task",
        "_trigger",
        "cancelled",
        "invocation_count",
        "last_invocation_length",
        "last_invoked_at",
        "started",
        "stopped",
    ]

    def __init__(
        self,
        func: TaskFunc,
        trigger: Trigger,
        auto_start: bool,
        max_failures: int,
        max_invocations: int,
    ) -> None:
        self._func = di.with_di(func)
        self._trigger = trigger
        self._auto_start = auto_start
        self._max_failures = max_failures
        self._max_invocations = max_invocations

        self.invocation_count: int = 0
        self.last_invocation_length: float = -1
        self.last_invoked_at: datetime.datetime | None = None

        self.started: bool = False
        self.stopped: bool = False
        self.cancelled: bool = False

        self._task: asyncio.Task[None] | None = None
        self._client: client.Client | None = None

    @property
    def running(self) -> bool:
        """
        Whether the task is running. A task is considered running if it has been started,
        but not stopped nor cancelled.
        """
        return self.started and not (self.stopped or self.cancelled)

    async def _loop(self) -> None:
        LOGGER.debug("starting task %r", self._func.__name__)

        assert self._client is not None
        self.started = True

        cancelled: asyncio.CancelledError | None = None

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
            async with (
                self._client.di.enter_context(di.Contexts.DEFAULT),
                self._client.di.enter_context(di.Contexts.TASK),
            ):
                try:
                    await self._func()
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError):
                        LOGGER.debug("task cancelled")
                        cancelled = e
                        break

                    n_failures += 1

                    if self._max_failures <= 0:
                        LOGGER.error(
                            "Execution of task %r failed", self._func.__name__, exc_info=(type(e), e, e.__traceback__)
                        )
                        continue

                    LOGGER.error(
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

        if cancelled is not None:
            raise asyncio.CancelledError from cancelled

        self.stopped, self._task = True, None
        LOGGER.debug("stopped task %r", self._func.__name__)

    def start(self) -> None:
        """
        Start the task. Does nothing if the task is already running.

        Returns:
            :obj:`None`

        Raises:
            :obj:`RuntimeError`: When trying to start a task that has not been added to a client, or the client
                it has been added to has not been started yet.
        """
        if self._client is None or not self._client._started:
            raise RuntimeError("cannot start a task for a non-started Client")

        if self.running:
            return

        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        """
        Stop the task. Does nothing if the task is already stopped, or has not been started.

        Returns:
            :obj:`None`
        """
        if not self.running:
            return

        self.stopped = True

    def cancel(self) -> asyncio.Task[t.Any] | None:
        """
        Cancel the task. Does nothing if the task is already stopped or canceled, or has not been started.

        Returns:
            :obj:`None`
        """
        if not self.running:
            return

        assert self._task is not None
        self._task.cancel()
        self._task = None

    async def await_completion(self) -> None:
        """
        Wait for the task to complete - either through stopping naturally or being cancelled.

        Returns:
            :obj:`None`
        """
        if self._task is None:
            return

        with contextlib.suppress(asyncio.CancelledError):
            await self._task
