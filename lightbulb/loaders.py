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

__all__ = ["Loadable", "Loader"]

import abc
import logging
import typing as t

import hikari

from lightbulb import di
from lightbulb import tasks

if t.TYPE_CHECKING:
    from lightbulb import client as client_
    from lightbulb.internal import types

CommandOrGroupT = t.TypeVar("CommandOrGroupT", bound="types.CommandOrGroup")
ErrorHandlerT = t.TypeVar("ErrorHandlerT", bound="types.ErrorHandler")
EventT = t.TypeVar("EventT", bound=hikari.Event)

LOGGER = logging.getLogger(__name__)


class Loadable(abc.ABC):
    """Abstract class containing the logic required to add and remove a feature from a client instance."""

    __slots__ = ()

    @abc.abstractmethod
    async def load(self, client: client_.Client) -> None:
        """
        Add the feature to the client instance.

        Args:
            client: The client instance to add the feature to.

        Returns:
            :obj:`None`

        Warning:
            This method **must** be idempotent. I.e. if the item being loaded is already loaded, the
            method **must not** attempt to load the item a second time.
        """

    @abc.abstractmethod
    async def unload(self, client: client_.Client) -> None:
        """
        Remove the feature from the client instance.

        Args:
            client: The client instance to remove the feature from.

        Returns:
            :obj:`None`

        Warning:
            This method **must** be idempotent. I.e. if the item being unloaded is already unloaded, the
            method **must not** attempt to unload the item a second time.
        """


class _CommandLoadable(Loadable):
    # TODO - check this is correctly idempotent
    __slots__ = ("_command", "_guilds", "_global", "_defer_guilds")

    def __init__(
        self,
        command: types.CommandOrGroup,
        guilds: t.Sequence[hikari.Snowflakeish] | None,
        global_: bool | None,
        defer_guilds: bool,
    ) -> None:
        self._command = command
        self._guilds = guilds
        self._global = global_
        self._defer_guilds = defer_guilds

    async def load(self, client: client_.Client) -> None:
        if self._defer_guilds:
            client.register(self._command, defer_guilds=True)
        else:
            client.register(self._command, guilds=self._guilds, global_=self._global)

    async def unload(self, client: client_.Client) -> None:
        client.unregister(self._command)


class _ListenerLoadable(Loadable):
    __slots__ = ("_callback", "_wrapped_callback", "_event_types")

    def __init__(self, callback: t.Callable[[EventT], t.Awaitable[None]], *event_types: type[EventT]) -> None:
        self._callback = callback
        self._event_types = event_types

        self._wrapped_callback: t.Callable[..., t.Awaitable[t.Any]] | None = None

    async def load(self, client: client_.Client) -> None:
        em = getattr(getattr(client, "_app", None), "event_manager", None)
        if not isinstance(em, hikari.api.EventManager):
            raise RuntimeError("listeners are not supported for non event_manager aware applications")

        async def _wrapped(*args: t.Any, **kwargs: t.Any) -> t.Any:
            async with client.di.enter_context(di.Contexts.LISTENER):
                return await self._callback(*args, **kwargs)

        self._wrapped_callback = _wrapped if di.DI_ENABLED else None

        for event in self._event_types:
            if (self._wrapped_callback or self._callback) in em.get_listeners(event):
                continue
            em.subscribe(event, self._wrapped_callback or self._callback)  # type: ignore[reportArgumentType]

    async def unload(self, client: client_.Client) -> None:
        em = getattr(getattr(client, "_app", None), "event_manager", None)
        assert isinstance(em, hikari.api.EventManager)

        for event in self._event_types:
            if (self._wrapped_callback or self._callback) not in em.get_listeners(event):
                continue
            em.unsubscribe(event, self._wrapped_callback or self._callback)  # type: ignore[reportArgumentType]


class _ErrorHandlerLoadable(Loadable):
    __slots__ = ("_callback", "_priority")

    def __init__(self, callback: types.ErrorHandler, priority: int) -> None:
        self._callback = callback
        self._priority = priority

    async def load(self, client: client_.Client) -> None:
        if self._callback in client._error_handlers[self._priority]:
            return
        client.error_handler(self._callback, priority=self._priority)

    async def unload(self, client: client_.Client) -> None:
        if self._callback not in client._error_handlers[self._priority]:
            return
        client.remove_error_handler(self._callback)


class _TaskLoadable(Loadable):
    __slots__ = ("_task",)

    def __init__(self, task: tasks.Task) -> None:
        self._task = task

    async def load(self, client: client_.Client) -> None:
        if self._task in client._tasks:
            return

        self._task = client.task(self._task)

    async def unload(self, client: client_.Client) -> None:
        if self._task not in client._tasks:
            return

        client.remove_task(self._task, cancel=True)


class Loader:
    """
    Class used for loading features into the client from extensions.

    Args:
        should_load_hook: Synchronous or asynchronous function which will be called when the loader is added to the
            client. Returns a boolean indicating whether this loader should be loaded or not. If it returns
            :obj:`False`, the loader **will not** be loaded and none of its features will be added to the client.
    """

    __slots__ = ("_should_load_hook", "_loadables")

    def __init__(self, should_load_hook: t.Callable[[], types.MaybeAwaitable[bool]] = lambda: True) -> None:
        self._should_load_hook = should_load_hook
        self._loadables: list[Loadable] = []

    async def add_to_client(self, client: client_.Client) -> None:
        """
        Add the features contained within this loader to the given client.

        Args:
            client: The client to add this loader's features to.

        Returns:
            :obj:`None`
        """
        for loadable in self._loadables:
            await loadable.load(client)

    async def remove_from_client(self, client: client_.Client) -> None:
        """
        Remove the features contained within this loader from the given client. If any single
        loadable's unload method raises an exception then the remaining loadables will still be unloaded.

        Args:
            client: The client to remove this loader's features from.

        Returns:
            :obj:`None`
        """
        for loadable in self._loadables:
            try:
                await loadable.unload(client)
            except Exception as e:
                LOGGER.warning("error while unloading loadable %r", loadable, exc_info=(type(e), e, e.__traceback__))

    def add(self, loadable: Loadable) -> Loadable:
        """
        Add the given loadable to this loader.

        Args:
            loadable: The loadable to add.

        Returns:
            The added loadable, unchanged.
        """
        self._loadables.append(loadable)
        return loadable

    @t.overload
    def command(
        self, *, guilds: t.Sequence[hikari.Snowflakeish] | None = None, global_: bool | None = None
    ) -> t.Callable[[CommandOrGroupT], CommandOrGroupT]: ...

    @t.overload
    def command(self, *, defer_guilds: t.Literal[True]) -> t.Callable[[CommandOrGroupT], CommandOrGroupT]: ...

    @t.overload
    def command(
        self,
        command: CommandOrGroupT,
        *,
        guilds: t.Sequence[hikari.Snowflakeish] | None = None,
        global_: bool | None = None,
    ) -> CommandOrGroupT: ...

    @t.overload
    def command(self, command: CommandOrGroupT, *, defer_guilds: t.Literal[True]) -> CommandOrGroupT: ...

    def command(
        self,
        command: CommandOrGroupT | None = None,
        *,
        guilds: t.Sequence[hikari.Snowflakeish] | None = None,
        global_: bool | None = None,
        defer_guilds: bool = False,
    ) -> CommandOrGroupT | t.Callable[[CommandOrGroupT], CommandOrGroupT]:
        """
        Register a command or group with this loader.

        This method can be used as a function, or a first or second order decorator.

        Args:
            command: The command class or command group to register with the client.
            guilds: The guilds to create the command or group in.
            global_: Whether the command should be registered globally.
            defer_guilds: Whether the guilds to create this command in should be resolved when the client is started.
                If :obj:`True`, the client's ``deferred_registration_callback`` will be used to resolve which guilds
                to create the command in. You can also use this to conditionally prevent the command from being
                registered to any guilds.

        Returns:
            The registered command or group, unchanged.

        Example:

            .. code-block:: python

                loader = lightbulb.Loader()

                # valid
                @loader.register
                # also valid
                @loader.register(guilds=[...])
                class Example(
                    lightbulb.SlashCommand,
                    ...
                ):
                    ...

                # also valid
                loader.register(Example, guilds=[...])

        See Also:
            :meth:`~lightbulb.client.Client.register`
        """
        # Used as a function or first-order decorator
        if command is not None:
            self.add(_CommandLoadable(command, guilds, global_, defer_guilds))
            return command

        # Used as a second-order decorator
        def _inner(command_: CommandOrGroupT) -> CommandOrGroupT:
            return self.command(command_, guilds=guilds)

        return _inner

    def listener(
        self, *event_types: type[EventT]
    ) -> t.Callable[
        [t.Callable["t.Concatenate[EventT, ...]", t.Awaitable[None]]], t.Callable[[EventT], t.Awaitable[None]]
    ]:
        """
        Decorator to register a listener with this loader. Also enables dependency injection on the listener
        callback.

        If an :obj:`hikari.api.event_manager.EventManager` instance is not available through dependency
        injection then adding this loader to the client will fail at runtime.

        Args:
            *event_types: The event class(es) for the listener to listen to.

        Example:

            .. code-block:: python

                loader = lightbulb.Loader()

                @loader.listener(hikari.MessageCreateEvent)
                async def message_create_listener(event: hikari.MessageCreateEvent) -> None:
                    ...
        """
        if not event_types:
            raise ValueError("you must specify at least one event type")

        def _inner(
            callback: t.Callable["t.Concatenate[EventT, ...]", t.Awaitable[None]],
        ) -> t.Callable[[EventT], t.Awaitable[None]]:
            wrapped = t.cast(t.Callable[[EventT], t.Awaitable[None]], di.with_di(callback))
            self.add(_ListenerLoadable(wrapped, *event_types))
            return wrapped

        return _inner

    @t.overload
    def error_handler(self, *, priority: int = 0) -> t.Callable[[ErrorHandlerT], ErrorHandlerT]: ...

    @t.overload
    def error_handler(self, func: ErrorHandlerT, *, priority: int = 0) -> ErrorHandlerT: ...

    def error_handler(
        self, func: ErrorHandlerT | None = None, *, priority: int = 0
    ) -> ErrorHandlerT | t.Callable[[ErrorHandlerT], ErrorHandlerT]:
        """
        Register an error handler function to call when an :obj:`~lightbulb.commands.execution.ExecutionPipeline` fails.
        Also enables dependency injection for the error handler function.

        The function must take the exception as its first argument, which will be an instance of
        :obj:`~lightbulb.exceptions.ExecutionPipelineFailedException`. The function **must** return a boolean
        indicating whether the exception was successfully handled. Non-boolean return values will be cast to booleans.

        Args:
            func: The function to register as a command error handler.
            priority: The priority that this handler should be registered at. Higher priority handlers
                will be executed first.
        """
        if func is not None:
            wrapped = di.with_di(func)
            self.add(_ErrorHandlerLoadable(wrapped, priority))
            return wrapped

        def _inner(func_: ErrorHandlerT) -> ErrorHandlerT:
            return self.error_handler(func_, priority=priority)

        return _inner

    def task(
        self, trigger: tasks.Trigger, /, auto_start: bool = True, max_failures: int = 1, max_invocations: int = -1
    ) -> t.Callable[[tasks.TaskFunc], tasks.Task]:
        """
        Second order decorator to register a repeating task with this loader. Task functions will have
        dependency injection enabled on them automatically. Task functions **must** be asynchronous.

        Args:
            trigger: The trigger function to use to resolve the interval between task executions.
            auto_start: Whether the task should be started automatically. This means that if the task is added to
                the client upon the client being started, the task will also be started; it will also be started
                if being added to an already-started client.
            max_failures: The maximum number of failed attempts to execute the task before it is cancelled.
            max_invocations: The maximum number of times the task can be invoked before being stopped.

        Example:

            .. code-block:: python

                loader = lightbulb.Loader()

                @loader.task(lightbulb.uniformtrigger(minutes=1))
                async def print_hi() -> None:
                    print("HI")
        """

        def _inner(func: tasks.TaskFunc) -> tasks.Task:
            task_obj = tasks.Task(func, trigger, auto_start, max_failures, max_invocations)
            self.add(_TaskLoadable(task_obj))
            return task_obj

        return _inner
