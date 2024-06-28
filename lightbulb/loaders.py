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
import svcs

from lightbulb.commands import commands
from lightbulb.commands import groups
from lightbulb.internal import di

if t.TYPE_CHECKING:
    from lightbulb import client as client_
    from lightbulb import exceptions

CommandOrGroup: t.TypeAlias = t.Union[type[commands.CommandBase], groups.Group]
CommandOrGroupT = t.TypeVar("CommandOrGroupT", bound=CommandOrGroup)
ErrorHandler: t.TypeAlias = t.Callable[
    "t.Concatenate[exceptions.ExecutionPipelineFailedException, ...]", t.Awaitable[bool]
]
ErrorHandlerT = t.TypeVar("ErrorHandlerT", bound=ErrorHandler)
EventT = t.TypeVar("EventT", bound=hikari.Event)

LOGGER = logging.getLogger("lightbulb.loaders")


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
        """

    async def unload(self, client: client_.Client) -> None:
        """
        Remove the feature from the client instance.

        Args:
            client: The client instance to remove the feature from.

        Returns:
            :obj:`None`
        """


class _CommandLoadable(Loadable):
    __slots__ = ("_command", "_guilds")

    def __init__(self, command: CommandOrGroup, guilds: t.Sequence[hikari.Snowflakeish] | None) -> None:
        self._command = command
        self._guilds = guilds

    async def load(self, client: client_.Client) -> None:
        client.register(self._command, guilds=self._guilds)

    async def unload(self, client: client_.Client) -> None:
        client.unregister(self._command)


class _ListenerLoadable(Loadable):
    __slots__ = ("_callback", "_wrapped_callback", "_event_types")

    def __init__(self, callback: t.Callable[[EventT], t.Awaitable[None]], *event_types: type[EventT]) -> None:
        self._callback = callback
        self._event_types = event_types

        self._wrapped_callback: t.Callable[..., t.Awaitable[t.Any]] | None = None

    async def load(self, client: client_.Client) -> None:
        try:
            event_manager = await client.di.get_dependency(hikari.api.EventManager)
        except svcs.exceptions.ServiceNotFoundError as e:
            raise RuntimeError("cannot load listeners as client does not support event dispatching") from e

        async def _wrapped(*args: t.Any, **kwargs: t.Any) -> t.Any:
            with di.ensure_di_context(client.di):
                return await self._callback(*args, **kwargs)

        self._wrapped_callback = _wrapped if di.DI_ENABLED else None

        for event in self._event_types:
            event_manager.subscribe(event, self._wrapped_callback or self._callback)  # type: ignore[reportArgumentType]

    async def unload(self, client: client_.Client) -> None:
        event_manager = await client.di.get_dependency(hikari.api.EventManager)

        for event in self._event_types:
            event_manager.unsubscribe(event, self._wrapped_callback or self._callback)  # type: ignore[reportArgumentType]


class _ErrorHandlerLoadable(Loadable):
    __slots__ = ("_callback", "_priority")

    def __init__(self, callback: ErrorHandler, priority: int) -> None:
        self._callback = callback
        self._priority = priority

    async def load(self, client: client_.Client) -> None:
        client.error_handler(self._callback, priority=self._priority)

    async def unload(self, client: client_.Client) -> None:
        client.remove_error_handler(self._callback)


class Loader:
    """Class used for loading features into the client from extensions."""

    __slots__ = ("_loadables",)

    def __init__(self) -> None:
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
        self, *, guilds: t.Sequence[hikari.Snowflakeish] | None = None
    ) -> t.Callable[[CommandOrGroupT], CommandOrGroupT]: ...

    @t.overload
    def command(
        self, command: CommandOrGroupT, *, guilds: t.Sequence[hikari.Snowflakeish] | None = None
    ) -> CommandOrGroupT: ...

    def command(
        self, command: CommandOrGroupT | None = None, *, guilds: t.Sequence[hikari.Snowflakeish] | None = None
    ) -> CommandOrGroupT | t.Callable[[CommandOrGroupT], CommandOrGroupT]:
        """
        Register a command or group with this loader. Optionally, a sequence of guild ids can
        be provided to make the commands created in specific guilds only - overriding the value for
        default enabled guilds.

        This method can be used as a function, or a first or second order decorator.

        Args:
            command: The command class or command group to register with the client.
            guilds: The guilds to create the command or group in. If set to :obj:`None`, then this will fall
                back to the default enabled guilds. To override default enabled guilds and make the command or
                group global, this should be set to an empty sequence.

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
        """
        # Used as a function or first-order decorator
        if command is not None:
            self.add(_CommandLoadable(command, guilds))
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
