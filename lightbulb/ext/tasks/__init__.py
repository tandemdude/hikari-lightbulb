# -*- coding: utf-8 -*-
# Copyright © tandemdude 2020-present
#
# This file is part of Lightbulb.
#
# Lightbulb is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Lightbulb is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Lightbulb. If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

__all__ = ["Task", "wait_until_started", "task", "load"]

import asyncio
import functools
import inspect
import logging
import typing as t

import hikari

if t.TYPE_CHECKING:
    import lightbulb

_LOGGER = logging.getLogger("lightbulb.ext.tasks")
TaskCallbackT = t.TypeVar("TaskCallbackT", bound=t.Callable[..., t.Union[t.Any, t.Coroutine[t.Any, t.Any, t.Any]]])
TaskErrorHandlerT = t.TypeVar(
    "TaskErrorHandlerT", bound=t.Callable[..., t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]]
)


class _BindableObjectWithCallback:
    __slots__ = ("_callback",)

    def __init__(self, callback: t.Callable[..., t.Any]) -> None:
        self._callback = callback

    def __get__(self, instance: t.Any, _: t.Type[t.Any]) -> _BindableObjectWithCallback:
        self._callback = functools.partial(self._callback, instance)
        return self

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        return self._callback(*args, **kwargs)


class Task(_BindableObjectWithCallback):
    __slots__ = (
        "_callback",
        "_next_interval",
        "_stopped",
        "_task",
        "_error_handler",
        "_consecutive_failures",
        "_max_consecutive_failures",
    )
    _app: t.Optional[lightbulb.BotApp] = None
    _app_starting: asyncio.Event = asyncio.Event()
    _app_started: asyncio.Event = asyncio.Event()
    _tasks: t.List[Task] = []

    def __init__(
        self, callback: TaskCallbackT, repeats: float, auto_start: bool, max_consecutive_failures: int
    ) -> None:
        super().__init__(callback)
        self._next_interval: float = repeats
        self._stopped: bool = False
        self._task: t.Optional[asyncio.Task[t.Any]] = None
        self._error_handler: t.Optional[
            t.Callable[[BaseException], t.Union[t.Any, t.Coroutine[t.Any, t.Any, t.Any]]]
        ] = None
        self._max_consecutive_failures: int = max_consecutive_failures
        self._consecutive_failures: int = 0

        if auto_start:
            self.start()

    def __get__(self, instance: t.Any, owner: t.Type[t.Any]) -> Task:
        super().__get__(instance, owner)
        return self

    @property
    def __name__(self) -> str:
        return getattr(
            self._callback.func if isinstance(self._callback, functools.partial) else self._callback,
            "__name__",
            "__unknown_name__",
        )

    @classmethod
    async def _app_starting_listener(cls, _: hikari.StartingEvent) -> None:
        assert Task._app is not None
        Task._app_starting.set()
        for task_ in Task._tasks:
            if not task_.is_running:
                task_.start()

    @classmethod
    async def _app_started_listener(cls, _: hikari.StartedEvent) -> None:
        assert Task._app is not None
        Task._app_started.set()

    @classmethod
    async def _app_stopping_listener(cls, _: hikari.StoppingEvent) -> None:
        assert Task._app is not None
        Task._app_starting.clear()
        Task._app_started.clear()
        for task_ in Task._tasks:
            task_.stop()

    async def _loop(self) -> None:
        while not self._stopped:
            _LOGGER.debug("Running task %r", self.__name__)
            try:
                maybe_coro = self._callback()
                if inspect.iscoroutine(maybe_coro):
                    await maybe_coro
                self._consecutive_failures = 0
            except Exception as e:
                out: t.Any = False

                if self._error_handler is not None:
                    out = self._error_handler(e)
                    if inspect.iscoroutine(out):
                        out = await out

                if not out:
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= self._max_consecutive_failures:
                        _LOGGER.error(
                            "Task failed repeatedly and has been cancelled", exc_info=(type(e), e, e.__traceback__)
                        )
                        break

                    _LOGGER.error(
                        "Error occurred during task execution and was not handled. "
                        "Task will be cancelled after %s more consecutive failure(s)",
                        self._max_consecutive_failures - self._consecutive_failures,
                        exc_info=(type(e), e, e.__traceback__),
                    )

            await asyncio.sleep(self._next_interval)

        assert self._task is not None
        self._task.cancel()
        Task._tasks.remove(self)
        self._task = None
        self._stopped = True
        _LOGGER.debug("Cancelled task %r", self.__name__)

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def update_interval(self, new_interval: float) -> None:
        self._next_interval = new_interval

    @t.overload
    def set_error_handler(self, func: TaskErrorHandlerT) -> TaskErrorHandlerT:
        ...

    @t.overload
    def set_error_handler(self) -> t.Callable[[TaskErrorHandlerT], TaskErrorHandlerT]:
        ...

    def set_error_handler(
        self, func: t.Optional[TaskErrorHandlerT] = None
    ) -> t.Union[TaskErrorHandlerT, t.Callable[[TaskErrorHandlerT], TaskErrorHandlerT]]:
        if func is not None:
            self._error_handler = _BindableObjectWithCallback(func)
            return self._error_handler

        def decorate(func_: TaskErrorHandlerT) -> TaskErrorHandlerT:
            self._error_handler = _BindableObjectWithCallback(func_)
            return self._error_handler

        return decorate

    def start(self) -> None:
        Task._tasks.append(self)
        if Task._app_starting.is_set():
            _LOGGER.debug("Starting task %r", self.__name__)
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self.is_running:
            self._stopped = True

    def cancel(self) -> None:
        if not self.is_running:
            return

        assert self._task is not None
        self._task.cancel()
        self._task = None
        self._stopped = True


async def wait_until_started() -> None:
    await Task._app_started.wait()


def task(
    *,
    s: float = 0,
    m: float = 0,
    h: float = 0,
    d: float = 0,
    auto_start: bool = False,
    max_consecutive_failures: int = 3,
) -> t.Callable[[TaskCallbackT], Task]:
    def decorate(func: TaskCallbackT) -> Task:
        if not any([s, m, h, d]):
            raise ValueError("Must provide a value to at least one of: 's', 'm', 'h', 'd'")
        return Task(func, s + (m * 60) + (h * 3600) + (d * 86400), auto_start, max(max_consecutive_failures, 1))

    return decorate


def load(app: lightbulb.BotApp) -> None:
    Task._app = app
    app.subscribe(hikari.StartingEvent, Task._app_starting_listener)
    app.subscribe(hikari.StoppingEvent, Task._app_stopping_listener)
