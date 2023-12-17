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
"""
An implementation of simple repeating asyncio tasks.

.. versionadded:: 2.2.0

Setup
-----

In order for tasks to function correctly you must first call :meth:`load` after initialising
your instance of the :obj:`~lightbulb.app.BotApp` class. See below:

.. code-block:: python

    import lightbulb
    from lightbulb.ext import tasks

    app = lightbulb.BotApp(...)
    tasks.load(app)

Creating Tasks
--------------

Tasks are created using the :obj:`~task` decorator.

.. code-block:: python

    from lightbulb.ext import tasks

    # s=30 means this will run every 30 seconds
    # you can also use (m)inutes, (h)ours, and (d)ays
    @tasks.task(s=30)
    async def print_every_30_seconds():
        print("Task called")

    # Instead of having to call .start() manually, you can pass auto_start=True
    # into the task decorator if you wish
    print_every_30_seconds.start()

See the :obj:`~task` decorator api reference for valid kwargs you can pass.

API Reference
-------------
"""
from __future__ import annotations

__all__ = ["load", "task", "wait_until_started", "Task", "Trigger", "UniformTrigger", "CronTrigger", "triggers"]

import asyncio
import functools
import inspect
import logging
import typing as t

import hikari

from . import triggers
from .triggers import *

if t.TYPE_CHECKING:
    import lightbulb

_LOGGER = logging.getLogger("lightbulb.ext.tasks")
TaskCallbackT = t.TypeVar("TaskCallbackT", bound=t.Callable[..., t.Union[t.Any, t.Coroutine[t.Any, t.Any, t.Any]]])
TaskErrorHandlerT = t.TypeVar(
    "TaskErrorHandlerT", bound=t.Callable[..., t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]]
)


class _BindableObjectWithCallback:
    __slots__ = ("_callback", "_bound")

    def __init__(self, callback: t.Callable[..., t.Any]) -> None:
        self._callback = callback
        self._bound: bool = False

    def __get__(self, instance: t.Any, _: t.Type[t.Any]) -> _BindableObjectWithCallback:
        if self._bound or instance is None:
            return self
        self._callback = functools.partial(self._callback, instance)
        return self

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        return self._callback(*args, **kwargs)


class Task(_BindableObjectWithCallback):
    """
    Class representing a repeating task.

    Args:
        callback: The function that will be executed every time the task is run.
        trigger (:obj:`.triggers.Trigger`): The task trigger to use.
        auto_start (:obj:`bool`): Whether the task will be automatically started when instantiated.
        max_consecutive_failures (:obj:`int`): The number of consecutive task failures that will be ignored
            before the task is cancelled.
        max_executions (Optional[:obj:`int`]): The maximum number of times that the task will be executed. If ``None``,
            the task will run indefinitely.
        pass_app (:obj:`bool`): Whether the :obj:`lightbulb.app.BotApp` object will be passed into the task upon
            execution.
    """

    __slots__ = (
        "_callback",
        "_trigger",
        "_stopped",
        "_task",
        "_error_handler",
        "_consecutive_failures",
        "_max_consecutive_failures",
        "_max_executions",
        "_n_executions",
        "_pass_app",
        "_wait_before_execution",
    )
    _app: t.Optional[lightbulb.BotApp] = None
    _app_starting: asyncio.Event = asyncio.Event()
    _app_started: asyncio.Event = asyncio.Event()
    _tasks: t.ClassVar[t.List[Task]] = []

    def __init__(
        self,
        callback: TaskCallbackT,
        trigger: triggers.Trigger,
        auto_start: bool,
        max_consecutive_failures: int,
        max_executions: t.Optional[int],
        pass_app: bool,
        wait_before_execution: hikari.UndefinedOr[bool],
    ) -> None:
        super().__init__(callback)
        self._trigger: triggers.Trigger = trigger
        self._stopped: bool = False
        self._task: t.Optional[asyncio.Task[t.Any]] = None
        self._error_handler: t.Optional[
            t.Callable[[BaseException], t.Union[t.Any, t.Coroutine[t.Any, t.Any, t.Any]]]
        ] = None
        self._max_consecutive_failures: int = max_consecutive_failures
        self._consecutive_failures: int = 0
        self._max_executions: t.Optional[int] = max_executions
        self._n_executions: int = 0
        self._pass_app: bool = pass_app
        self._wait_before_execution: bool = (
            wait_before_execution if wait_before_execution is not hikari.UNDEFINED else trigger.wait_before_execution
        )

        if auto_start:
            self.start()

    def __get__(self, instance: t.Any, owner: t.Type[t.Any]) -> Task:
        # We override this to keep linters happy
        super().__get__(instance, owner)
        return self

    @property
    def __name__(self) -> str:
        return getattr(
            self._callback.func if isinstance(self._callback, functools.partial) else self._callback,
            "__name__",
            "__unknown_name__",
        )

    @property
    def _is_event_loop_running(self) -> bool:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return False
        return True

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
        if self._wait_before_execution:
            await asyncio.sleep(self._trigger.get_interval())

        while not self._stopped:
            if self._max_executions is not None and self._n_executions >= self._max_executions:
                break

            _LOGGER.debug("Running task %r", self.__name__)
            self._n_executions += 1
            try:
                maybe_coro = self._callback(*([Task._app] if self._pass_app else []))
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

            await asyncio.sleep(self._trigger.get_interval())

        assert self._task is not None
        self._task.cancel()
        Task._tasks.remove(self)
        self._task = None
        self._stopped = True
        self._n_executions = 0
        _LOGGER.debug("Stopped task %r", self.__name__)

    @property
    def n_executions(self) -> int:
        """The number of times the task has been executed since being started."""
        return self._n_executions

    @property
    def is_running(self) -> bool:
        """Whether the task represented by this object is currently running or not."""
        return self._task is not None and not self._task.done()

    @t.overload
    def set_error_handler(self, func: TaskErrorHandlerT) -> TaskErrorHandlerT:
        ...

    @t.overload
    def set_error_handler(self) -> t.Callable[[TaskErrorHandlerT], TaskErrorHandlerT]:
        ...

    def set_error_handler(
        self, func: t.Optional[TaskErrorHandlerT] = None
    ) -> t.Union[TaskErrorHandlerT, t.Callable[[TaskErrorHandlerT], TaskErrorHandlerT]]:
        """
        Sets the function to use as the error handler for this task. This can be used as a first
        or second order decorator, or called with the function to set as the error handler.

        The error handler should return a boolean indicating whether the error could be handled.
        If ``False`` or a falsy value is returned, the related execution of the task will be considered
        to be a failure.
        """
        if func is not None:
            if isinstance(func, _BindableObjectWithCallback):
                return self._error_handler  # type: ignore[unreachable]
            self._error_handler = _BindableObjectWithCallback(func)
            return self._error_handler

        def decorate(func_: TaskErrorHandlerT) -> TaskErrorHandlerT:
            if isinstance(func_, _BindableObjectWithCallback):
                return func_  # type: ignore[unreachable]
            self._error_handler = _BindableObjectWithCallback(func_)
            return self._error_handler

        return decorate

    def start(self) -> None:
        """
        Start the task if the event loop has been established, or schedule the task to be started
        once the event loop has been established.

        Returns:
            ``None``
        """
        Task._tasks.append(self)
        if self._is_event_loop_running:
            _LOGGER.debug("Starting task %r", self.__name__)
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        """
        Stop the task after the completion of the current iteration, if it was running.

        Returns:
            ``None``
        """
        if self.is_running:
            self._stopped = True

    def cancel(self) -> None:
        """
        Cancel the task if it was running.

        Returns:
            ``None``
        """
        if not self.is_running:
            return

        assert self._task is not None
        self._task.cancel()
        self._task = None
        self._stopped = True
        self._n_executions = 0


async def wait_until_started() -> None:
    """
    Wait until the bot has started. Note that :obj:`.load` **must** have been
    called in order for this to function.

    Roughly equivalent to:

    .. code-block:: python

        # Where app is an instance of 'lightbulb.BotApp'
        await app.wait_for(hikari.StartedEvent, timeout=None)

    Returns:
        ``None``
    """
    await Task._app_started.wait()


@t.overload
def task(
    *,
    s: float = 0,
    m: float = 0,
    h: float = 0,
    d: float = 0,
    auto_start: bool = False,
    max_consecutive_failures: int = 3,
    max_executions: t.Optional[int] = None,
    pass_app: bool = False,
    wait_before_execution: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    cls: t.Type[Task] = Task,
) -> t.Callable[[TaskCallbackT], Task]:
    ...


@t.overload
def task(
    trigger: triggers.Trigger,
    /,
    *,
    auto_start: bool = False,
    max_consecutive_failures: int = 3,
    max_executions: t.Optional[int] = None,
    pass_app: bool = False,
    wait_before_execution: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    cls: t.Type[Task] = Task,
) -> t.Callable[[TaskCallbackT], Task]:
    ...


@t.overload
def task(
    trigger: t.Type[triggers.UniformTrigger],
    /,
    *,
    s: float = 0,
    m: float = 0,
    h: float = 0,
    d: float = 0,
    auto_start: bool = False,
    max_consecutive_failures: int = 3,
    max_executions: t.Optional[int] = None,
    pass_app: bool = False,
    wait_before_execution: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    cls: t.Type[Task] = Task,
) -> t.Callable[[TaskCallbackT], Task]:
    ...


def task(
    trigger: t.Optional[t.Union[triggers.Trigger, t.Type[triggers.Trigger]]] = None,
    /,
    *,
    s: float = 0,
    m: float = 0,
    h: float = 0,
    d: float = 0,
    auto_start: bool = False,
    max_consecutive_failures: int = 3,
    max_executions: t.Optional[int] = None,
    pass_app: bool = False,
    wait_before_execution: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    cls: t.Type[Task] = Task,
) -> t.Callable[[TaskCallbackT], Task]:
    """
    Second order decorator to register a function as a repeating task. The decorated function can
    be a synchronous or asynchronous function, and any return value will be discarded.

    Args:
        trigger (Optional[:obj:`~.triggers.Trigger`]): Trigger to use to set the interval between task executions.
            If not provided, and interval values were provided then this defaults to :obj:`~.triggers.UniformTrigger`.

    Keyword Args:
        s (:obj:`float`): Number of seconds between task executions.
        m (:obj:`float`): Number of minutes between task executions.
        h (:obj:`float`): Number of hours between task executions.
        d (:obj:`float`): Number of days between task executions.
        auto_start (:obj:`bool`): Whether the task will be started automatically when created. If ``False``,
            :meth:`~Task.start` will have to be called manually in order to start the task's execution.
        max_consecutive_failures (:obj:`int`): The number of consecutive task failures that will be ignored
            before the task's execution is cancelled. Defaults to ``3``, minimum ``1``.
        max_executions (Optional[:obj:`int`]): The maximum number of times that the task will run. If ``None``, the
            task will run indefinitely.
        pass_app (:obj:`bool`): Whether the :obj:`lightbulb.app.BotApp` instance should be passed into the
            task on execution. Defaults to ``False``.
        wait_before_execution (UndefinedOr[:obj:`bool`]): Whether the task will wait its given interval before the first
            time the task is executed. Defaults to ``UNDEFINED`` (will use the trigger's default).
        cls (Type[:obj:`~Task`]): Task class to use.

    .. versionadded:: 2.2.2
        ``wait_before_execution`` kwarg.
    """

    def decorate(func: TaskCallbackT) -> Task:
        nonlocal trigger

        if any([s, m, h, d]):
            trigger = trigger or triggers.UniformTrigger
            assert inspect.isclass(trigger) and issubclass(trigger, triggers.UniformTrigger)
            return cls(
                func,
                (trigger or triggers.UniformTrigger)(s + (m * 60) + (h * 3600) + (d * 86400)),
                auto_start,
                max(max_consecutive_failures, 1),
                max_executions,
                pass_app,
                wait_before_execution,
            )

        if trigger is None:
            raise ValueError("Interval values were not provided and no trigger was passed")

        assert isinstance(trigger, triggers.Trigger)
        return cls(
            func, trigger, auto_start, max(max_consecutive_failures, 1), max_executions, pass_app, wait_before_execution
        )

    return decorate


def load(app: lightbulb.BotApp) -> None:
    """
    Add the task system to the bot, enabling tasks to be run
    once the bot has started.

    Args:
        app (:obj:`~lightbulb.app.BotApp`): :obj:`~lightbulb.app.BotApp` instance
            that tasks will be enabled for.

    Returns:
        ``None``
    """
    Task._app = app
    app.subscribe(hikari.StartingEvent, Task._app_starting_listener)
    app.subscribe(hikari.StartedEvent, Task._app_started_listener)
    app.subscribe(hikari.StoppingEvent, Task._app_stopping_listener)
