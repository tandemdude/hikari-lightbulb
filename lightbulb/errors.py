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

__all__: typing.Final[typing.List[str]] = [
    "CommandErrorEvent",
    "LightbulbError",
    "ExtensionError",
    "ExtensionAlreadyLoaded",
    "ExtensionNotLoaded",
    "ExtensionMissingLoad",
    "ExtensionMissingUnload",
    "CommandError",
    "CommandNotFound",
    "NotEnoughArguments",
    "TooManyArguments",
    "ConverterFailure",
    "CommandIsOnCooldown",
    "CommandSyntaxError",
    "PrematureEOF",
    "UnclosedQuotes",
    "CheckFailure",
    "OnlyInGuild",
    "OnlyInDM",
    "NotOwner",
    "BotOnly",
    "HumanOnly",
    "MissingRequiredRole",
    "MissingRequiredPermission",
    "BotMissingRequiredPermission",
]

import abc
import typing

import attr
import hikari

from lightbulb import commands
from lightbulb import context as context_

if typing.TYPE_CHECKING:
    import types


@attr.s(kw_only=True, slots=True)
class CommandErrorEvent(hikari.Event):
    """
    Event type to subscribe to for the processing of all command errors raised by the handler.

    Example:

        .. code-block:: python

            from lightbulb.errors import CommandErrorEvent

            bot = lightbulb.Bot(token="token_here", prefix="!")

            @bot.listen(CommandErrorEvent)
            async def handle_command_error(error):
                ...

    """

    app: hikari.api.event_consumer.IEventConsumerApp = attr.ib()
    """App instance for this application."""
    exception: LightbulbError = attr.ib()
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


class LightbulbError(Exception):
    """Base for any exception raised by lightbulb."""


class ExtensionError(LightbulbError):
    """Base exception for errors incurred during the loading and unloading of extensions."""

    pass


class ExtensionAlreadyLoaded(ExtensionError):
    """Exception raised when an extension already loaded is attempted to be loaded."""

    pass


class ExtensionNotLoaded(ExtensionError):
    """Exception raised when an extension not already loaded is attempted to be unloaded."""

    pass


class ExtensionMissingLoad(ExtensionError):
    """Exception raised when an extension is attempted to be loaded but does not contain a load function"""

    pass


class ExtensionMissingUnload(ExtensionError):
    """Exception raised when an extension is attempted to be unloaded but does not contain an unload function"""

    pass


class CommandError(LightbulbError):
    """Base exception for errors incurred during handling od commands."""

    pass


class CommandNotFound(CommandError):
    """
    Exception raised when a command when attempted to be invoked but one with that name could not be found.

    Args:
        invoked_with (:obj:`str`): The command string that was attempted to be invoked.
    """

    def __init__(self, invoked_with: str) -> None:
        self.invoked_with = invoked_with


class NotEnoughArguments(CommandError):
    """
    Exception raised when a command is run without a sufficient number of arguments.

    Args:
        invoked_with (:obj:`str`): The command string that was attempted to be invoked
    """

    def __init__(self, invoked_with: str) -> None:
        self.invoked_with = invoked_with


class TooManyArguments(CommandError):
    """
    Exception raised when a command is run with too many arguments, and the command has been
    defined to not accept any extra arguments when invoked.

    Args:
        invoked_with (:obj:`str`): The command string that was attempted to be invoked
    """

    def __init__(self, invoked_with: str) -> None:
        self.invoked_with = invoked_with


class ConverterFailure(CommandError):
    """
    Exception raised when a converter for a command argument fails.
    """

    pass


class CommandIsOnCooldown(CommandError):
    """
    Exception raised when a command is attempted to be run but is currently on cooldown.

    Args:
        text (:obj:`str`): The error text.

    Keyword Args:
        command (:obj:`~.commands.Command`): The command that is on cooldown.
        retry_in (:obj:`float`): Number of seconds remaining for the cooldown.
    """

    def __init__(self, text: str, *, command: commands.Command, retry_in: float) -> None:
        self.text = text
        self.command = command
        self.retry_in = retry_in


class CommandSyntaxError(CommandError, abc.ABC):
    """
    Base error raised if a syntax issue occurs parsing invocation arguments.
    """

    # Forces the class to be abstract.
    @abc.abstractmethod
    def __init__(self):
        ...


class PrematureEOF(CommandSyntaxError):
    """
    Error raised if EOF (end of input) was reached, but more content was 
    expected.
    """

    def __init__(self) -> None:
        # Required to override the abstract super init.
        super().__init__()


class UnclosedQuotes(CommandSyntaxError):
    """
    Error raised when no closing quote is found for a quoted argument.

    Args:
        text (:obj:`str`): The text that caused the error to be raised.
    """

    def __init__(self, text: str) -> None:
        # Required to override the abstract super init.
        super().__init__()
        self.text = text


class CheckFailure(CommandError):
    """
    Base error that is raised when a check fails for a command. Anything raised by a check
    should inherit from this class.
    """

    pass


class OnlyInGuild(CheckFailure):
    """
    Error raised when a command marked as guild only is attempted to be invoked in DMs.
    """

    pass


class OnlyInDM(CheckFailure):
    """
    Error raised when a command marked as DM only is attempted to be invoked in a guild.
    """

    pass


class NotOwner(CheckFailure):
    """
    Error raised when a command marked as owner only is attempted to be invoked by another user.
    """

    pass


class BotOnly(CheckFailure):
    """
    Error raised when the command invoker is not a bot.
    """

    pass


class HumanOnly(CheckFailure):
    """
    Error raised when the command invoker is not an human.
    """

    pass


class MissingRequiredRole(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more role required.
    """

    pass


class MissingRequiredPermission(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more permission required.

    Args:
        text (:obj:`str`): The error text.

    Keyword Args:
        permissions (Sequence[ :obj:`hikari.Permissions` ]: Permission(s) the member is missing.
    """

    def __init__(self, text: str, *, permissions: typing.Sequence[hikari.Permissions]) -> None:
        self.text = text
        self.permissions = permissions


class BotMissingRequiredPermission(CheckFailure):
    """
    Error raised when the bot is missing one or more permission required for the command to be run.

    Args:
        text (:obj:`str`): The error text.

    Keyword Args:
        permissions (Sequence[ :obj:`hikari.Permissions` ]: Permission(s) the bot is missing.
    """

    def __init__(self, text: str, *, permissions: typing.Sequence[hikari.Permissions]) -> None:
        self.text = text
        self.permissions = permissions
