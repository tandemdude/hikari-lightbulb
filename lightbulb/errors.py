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
    "NSFWChannelOnly",
    "MissingRequiredRole",
    "MissingRequiredPermission",
    "BotMissingRequiredPermission",
    "CommandInvocationError",
]

import abc
import typing

import attr
import hikari

from lightbulb import commands


@attr.s(slots=True, weakref_slot=False)
class LightbulbError(Exception):
    """Base for any exception raised by lightbulb."""


@attr.s(slots=True, weakref_slot=False)
class ExtensionError(LightbulbError):
    """Base exception for errors incurred during the loading and unloading of extensions."""


@attr.s(slots=True, weakref_slot=False)
class ExtensionAlreadyLoaded(ExtensionError):
    """Exception raised when an extension already loaded is attempted to be loaded."""


@attr.s(slots=True, weakref_slot=False)
class ExtensionNotLoaded(ExtensionError):
    """Exception raised when an extension not already loaded is attempted to be unloaded."""


@attr.s(slots=True, weakref_slot=False)
class ExtensionMissingLoad(ExtensionError):
    """Exception raised when an extension is attempted to be loaded but does not contain a load function"""


@attr.s(slots=True, weakref_slot=False)
class ExtensionMissingUnload(ExtensionError):
    """Exception raised when an extension is attempted to be unloaded but does not contain an unload function"""


@attr.s(slots=True, weakref_slot=False)
class CommandError(LightbulbError):
    """Base exception for errors incurred during handling of commands."""


@attr.s(slots=True, weakref_slot=False)
class CommandNotFound(CommandError):
    """
    Exception raised when a command when attempted to be invoked but one with that name could not be found.
    """

    invoked_with: str = attr.ib()
    """The command string that was attempted to be invoked."""


@attr.s(slots=True, weakref_slot=False)
class NotEnoughArguments(CommandError):
    """
    Exception raised when a command is run without a sufficient number of arguments.
    """

    invoked_with: str = attr.ib()
    """The command string that was attempted to be invoked."""


@attr.s(slots=True, weakref_slot=False)
class TooManyArguments(CommandError):
    """
    Exception raised when a command is run with too many arguments, and the command has been
    defined to not accept any extra arguments when invoked.
    """

    invoked_with: str = attr.ib()
    """The command string that was attempted to be invoked."""


@attr.s(slots=True, weakref_slot=False)
class ConverterFailure(CommandError):
    """
    Exception raised when a converter for a command argument fails.
    """


@attr.s(slots=True, weakref_slot=False)
class CommandIsOnCooldown(CommandError):
    """
    Exception raised when a command is attempted to be run but is currently on cooldown.
    """

    text: str = attr.ib()
    """The error text."""

    command: commands.Command = attr.ib(kw_only=True)
    """The command that is on cooldown."""

    retry_in: float = attr.ib(kw_only=True)
    """Number of seconds remaining for the cooldown."""


@attr.s(slots=True, weakref_slot=False)
class CommandSyntaxError(CommandError, abc.ABC):
    """
    Base error raised if a syntax issue occurs parsing invocation arguments.
    """

    # Forces the class to be abstract.
    @abc.abstractmethod
    def __init__(self) -> None:
        ...


@attr.s(slots=True, init=False, weakref_slot=False)
class PrematureEOF(CommandSyntaxError):
    """
    Error raised if EOF (end of input) was reached, but more content was
    expected.
    """

    def __init__(self) -> None:
        # Required to override the abstract super init.
        super().__init__()


@attr.s(slots=True, init=False, weakref_slot=False)
class UnclosedQuotes(CommandSyntaxError):
    """
    Error raised when no closing quote is found for a quoted argument.
    """

    text: str = attr.ib()
    """The text that caused the error to be raised."""

    def __init__(self, text: str) -> None:
        # Required to override the abstract super init.
        super().__init__()
        self.text = text


@attr.s(slots=True, weakref_slot=False)
class CheckFailure(CommandError):
    """
    Base error that is raised when a check fails for a command. Anything raised by a check
    should inherit from this class.
    """

    text: typing.Optional[str] = attr.ib(default=None)
    """The error text."""


@attr.s(slots=True, weakref_slot=False)
class OnlyInGuild(CheckFailure):
    """
    Error raised when a command marked as guild only is attempted to be invoked in DMs.
    """


@attr.s(slots=True, weakref_slot=False)
class OnlyInDM(CheckFailure):
    """
    Error raised when a command marked as DM only is attempted to be invoked in a guild.
    """


@attr.s(slots=True, weakref_slot=False)
class NotOwner(CheckFailure):
    """
    Error raised when a command marked as owner only is attempted to be invoked by another user.
    """


@attr.s(slots=True, weakref_slot=False)
class BotOnly(CheckFailure):
    """
    Error raised when the command invoker is not a bot.
    """


@attr.s(slots=True, weakref_slot=False)
class HumanOnly(CheckFailure):
    """
    Error raised when the command invoker is not an human.
    """


@attr.s(slots=True, weakref_slot=False)
class NSFWChannelOnly(CheckFailure):
    """
    Error raised when a command that must be invoked in an NSFW channel is attempted to be invoked outside of one.
    """


@attr.s(slots=True, weakref_slot=False)
class MissingRequiredRole(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more role required.
    """


@attr.s(slots=True, weakref_slot=False)
class MissingRequiredPermission(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more permission required.
    """

    text: typing.Optional[str] = attr.ib(default=None)
    """The error text."""
    permissions: hikari.Permissions = attr.ib(kw_only=True)
    """Permission(s) the bot is missing."""


@attr.s(slots=True, weakref_slot=False)
class BotMissingRequiredPermission(CheckFailure):
    """
    Error raised when the bot is missing one or more permission required for the command to be run.
    """

    text: typing.Optional[str] = attr.ib(default=None)
    """The error text."""
    permissions: hikari.Permissions = attr.ib(kw_only=True)
    """Permission(s) the bot is missing."""


@attr.s(slots=True, weakref_slot=False)
class CommandInvocationError(CommandError):
    """
    Error raised if an error is encountered during command invocation. This will only be raised
    if all the checks passed and an error was raised somewhere inside the command.
    This effectively acts as a wrapper for the original exception for easier handling in an error handler.
    """

    text: str = attr.ib()
    """The error text."""
    original: Exception = attr.ib()
    """The original exception that caused this to be raised."""

    @property
    def __cause__(self) -> Exception:
        return self.original
