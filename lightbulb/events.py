# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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

__all__: typing.Final[typing.List[str]] = ["CommandErrorEvent", "CommandInvocationEvent", "CommandCompletionEvent"]

import abc
import typing

import attr
import hikari

if typing.TYPE_CHECKING:
    import types

    from lightbulb import commands
    from lightbulb import context as context_
    from lightbulb import errors


@attr.s(slots=True)
class LightbulbEvent(hikari.Event, abc.ABC):
    """
    The base class for all lightbulb events. Every event dispatched by lightbulb
    will be an instance of a subclass of this.
    """

    pass


@attr.s(kw_only=True, slots=True)
class CommandErrorEvent(LightbulbEvent):
    """
    Event type to subscribe to for the processing of all command errors raised by the handler.

    Example:

        .. code-block:: python

            from lightbulb.events import CommandErrorEvent

            bot = lightbulb.Bot(token="token_here", prefix="!")

            @bot.listen(CommandErrorEvent)
            async def handle_command_error(event):
                ...

    """

    app: hikari.api.event_consumer.IEventConsumerApp = attr.ib()
    """App instance for this application."""
    exception: errors.LightbulbError = attr.ib()
    """The exception that triggered this event."""
    context: typing.Optional[context_.Context] = attr.ib(default=None)
    """The context that this event was triggered for. Will be ``None`` for :obj:`~CommandNotFound` errors."""
    message: hikari.Message = attr.ib()
    """The message that this event was triggered for."""
    command: typing.Optional[commands.Command] = attr.ib(default=None)
    """The command that this event was triggered for."""

    @property
    def traceback(self) -> types.TracebackType:
        """The traceback for this event's exception."""
        return self.exception.__traceback__


@attr.s(kw_only=True, slots=True)
class CommandInvocationEvent(LightbulbEvent):
    """
    Event dispatched when a command is invoked, regardless of whether or not the checks
    passed or failed, or an error was raised during command invocation.
    """

    app: hikari.api.event_consumer.IEventConsumerApp = attr.ib()
    """App instance for this application."""
    command: commands.Command = attr.ib()
    """The command that this event was triggered for."""
    context: context_.Context = attr.ib()
    """The context that this event was triggered for."""


@attr.s(kw_only=True, slots=True)
class CommandCompletionEvent(LightbulbEvent):
    """
    Event type dispatched when a command invocation occurred and was completed successfully. This means
    that all checks must have passed and that no errors can have been raised during the command invocation.
    """

    app: hikari.api.event_consumer.IEventConsumerApp = attr.ib()
    """App instance for this application."""
    command: commands.Command = attr.ib()
    """The command that this event was triggered for."""
    context: context_.Context = attr.ib()
    """The context that this event was triggered for."""
