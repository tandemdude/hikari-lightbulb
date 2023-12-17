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

__all__ = [
    "LightbulbEvent",
    "LightbulbStartedEvent",
    "CommandErrorEvent",
    "PrefixCommandErrorEvent",
    "PrefixCommandInvocationEvent",
    "PrefixCommandCompletionEvent",
    "SlashCommandErrorEvent",
    "CommandInvocationEvent",
    "SlashCommandInvocationEvent",
    "SlashCommandCompletionEvent",
    "MessageCommandErrorEvent",
    "CommandCompletionEvent",
    "MessageCommandCompletionEvent",
    "MessageCommandInvocationEvent",
    "UserCommandErrorEvent",
    "UserCommandCompletionEvent",
    "UserCommandInvocationEvent",
]

import abc
import typing as t

import attr
import hikari

if t.TYPE_CHECKING:
    import types

    from lightbulb import app as app_
    from lightbulb import commands
    from lightbulb import context as context_
    from lightbulb import errors


@attr.s(slots=True, weakref_slot=False)
class LightbulbEvent(hikari.Event, abc.ABC):
    """
    The base class for all lightbulb events. Every event dispatched by lightbulb
    will be an instance of a subclass of this.
    """

    app: app_.BotApp = attr.ib()
    """BotApp instance for this event."""

    @property
    def bot(self) -> app_.BotApp:
        """BotApp instance for this event. Alias for :obj:`~LightbulbEvent.app`."""
        return self.app


@attr.s(slots=True, weakref_slot=False)
class LightbulbStartedEvent(LightbulbEvent):
    """
    Event dispatched after the application commands have been managed.

    .. versionadded:: 2.1.0
    """


@attr.s(slots=True, weakref_slot=False)
class CommandErrorEvent(LightbulbEvent, abc.ABC):
    """
    The base class for all command error events. A subclass of this event will be dispatched whenever
    an error is encountered before or during the invocation of a command.
    """

    exception: errors.LightbulbError = attr.ib()
    """The exception that this event was triggered for."""
    context: context_.base.Context = attr.ib()
    """The context that this event was triggered for."""

    @property
    def exc_info(
        self,
    ) -> t.Tuple[t.Type[errors.LightbulbError], errors.LightbulbError, t.Optional[types.TracebackType]]:
        """The exception triplet compatible with context managers and :mod:`traceback` helpers."""
        return type(self.exception), self.exception, self.exception.__traceback__


@attr.s(slots=True, weakref_slot=False)
class CommandInvocationEvent(LightbulbEvent, abc.ABC):
    """
    The base class for all command invocation events. A subclass of this event will be dispatched before
    any command is invoked.
    """

    command: commands.base.Command = attr.ib()
    """The command that this event was triggered for."""
    context: context_.base.Context = attr.ib()
    """The context that this event was triggered for."""


@attr.s(slots=True, weakref_slot=False)
class CommandCompletionEvent(LightbulbEvent, abc.ABC):
    """
    The base class for all command completion events. A subclass of this event will be dispatched after
    command invocation completes. This will not be dispatched if any exceptions occur during invocation.
    """

    command: commands.base.Command = attr.ib()
    """The command that this event was triggered for."""
    context: context_.base.Context = attr.ib()
    """The context that this event was triggered for."""


@attr.s(slots=True, weakref_slot=False)
class PrefixCommandErrorEvent(CommandErrorEvent):
    """Event dispatched when an error is encountered before or during the invocation of a prefix command."""


@attr.s(slots=True, weakref_slot=False)
class SlashCommandErrorEvent(CommandErrorEvent):
    """Event dispatched when an error is encountered before or during the invocation of a slash command."""


@attr.s(slots=True, weakref_slot=False)
class MessageCommandErrorEvent(CommandErrorEvent):
    """Event dispatched when an error is encountered before or during the invocation of a message command."""


@attr.s(slots=True, weakref_slot=False)
class UserCommandErrorEvent(CommandErrorEvent):
    """Event dispatched when an error is encountered before or during the invocation of a user command."""


@attr.s(slots=True, weakref_slot=False)
class PrefixCommandInvocationEvent(CommandInvocationEvent):
    """Event dispatched before the invocation of a prefix command."""


@attr.s(slots=True, weakref_slot=False)
class SlashCommandInvocationEvent(CommandInvocationEvent):
    """Event dispatched before the invocation of a slash command."""


@attr.s(slots=True, weakref_slot=False)
class MessageCommandInvocationEvent(CommandInvocationEvent):
    """Event dispatched before the invocation of a message command."""


@attr.s(slots=True, weakref_slot=False)
class UserCommandInvocationEvent(CommandInvocationEvent):
    """Event dispatched before the invocation of a user command."""


@attr.s(slots=True, weakref_slot=False)
class PrefixCommandCompletionEvent(CommandCompletionEvent):
    """Event dispatched after the invocation of a prefix command is completed."""


@attr.s(slots=True, weakref_slot=False)
class SlashCommandCompletionEvent(CommandCompletionEvent):
    """Event dispatched after the invocation of a slash command is completed."""


@attr.s(slots=True, weakref_slot=False)
class MessageCommandCompletionEvent(CommandCompletionEvent):
    """Event dispatched after the invocation of a message command is completed."""


@attr.s(slots=True, weakref_slot=False)
class UserCommandCompletionEvent(CommandCompletionEvent):
    """Event dispatched after the invocation of a user command is completed."""
