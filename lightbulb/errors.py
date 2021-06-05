# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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
    "MissingRequiredAttachment",
    "CommandInvocationError",
]

import abc
import typing

import hikari

from lightbulb import commands


class LightbulbError(Exception):
    """Base for any exception raised by lightbulb."""


class ExtensionError(LightbulbError):
    """Base exception for errors incurred during the loading and unloading of extensions."""

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class ExtensionAlreadyLoaded(ExtensionError):
    """Exception raised when an extension already loaded is attempted to be loaded."""


class ExtensionNotLoaded(ExtensionError):
    """Exception raised when an extension not already loaded is attempted to be unloaded."""


class ExtensionMissingLoad(ExtensionError):
    """Exception raised when an extension is attempted to be loaded but does not contain a load function"""


class ExtensionMissingUnload(ExtensionError):
    """Exception raised when an extension is attempted to be unloaded but does not contain an unload function"""


class CommandError(LightbulbError):
    """Base exception for errors incurred during handling of commands."""


class CommandNotFound(CommandError):
    """
    Exception raised when a command when attempted to be invoked but one with that name could not be found.
    """

    def __init__(self, invoked_with: str) -> None:
        self.invoked_with: str = invoked_with
        """The command string that was attempted to be invoked."""


class NotEnoughArguments(CommandError):
    """
    Exception raised when a command is run without a sufficient number of arguments.
    """

    def __init__(self, command: commands.Command, missing_args: typing.List[str]) -> None:
        self.command: commands.Command = command
        """The command string that was attempted to be invoked."""
        self.missing_args: typing.List[str] = missing_args
        """The required arguments that are missing."""


class TooManyArguments(CommandError):
    """
    Exception raised when a command is run with too many arguments, and the command has been
    defined to not accept any extra arguments when invoked.
    """

    def __init__(self, command: commands.Command) -> None:
        self.command: commands.Command = command
        """The command string that was attempted to be invoked."""


class ConverterFailure(CommandError):
    """
    Exception raised when a converter for a command argument fails.
    """

    def __init__(self, text: typing.Optional[str] = None) -> None:
        self.text: typing.Optional[str] = text
        """The error text."""


class CommandIsOnCooldown(CommandError):
    """
    Exception raised when a command is attempted to be run but is currently on cooldown.
    """

    def __init__(self, text: str, command: commands.Command, retry_in: float) -> None:
        self.text: str = text
        """The error text."""

        self.command: commands.Command = command
        """The command that is on cooldown."""

        self.retry_in: float = retry_in
        """Number of seconds remaining for the cooldown."""


class CommandSyntaxError(CommandError, abc.ABC):
    """
    Base error raised if a syntax issue occurs parsing invocation arguments.
    """

    # Forces the class to be abstract.
    @abc.abstractmethod
    def __init__(self) -> None:
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
    """

    def __init__(self, text: str) -> None:
        # Required to override the abstract super init.
        super().__init__()
        self.text = text
        """The text that caused the error to be raised."""


class UnexpectedQuotes(CommandSyntaxError):
    """
    Error raised when a quote mark is found in non-quoted string.
    """

    def __init__(self, quote: str) -> None:
        super().__init__()
        self.quote = quote
        """The quote mark that caused the error to be raised."""


class ExpectedSpaces(CommandSyntaxError):
    """
    Error raised when no spaces found in the end of a quoted string
    """

    def __init__(self, char: str) -> None:
        super().__init__()
        self.char = char
        """The character that's expected to be a space character"""


class CheckFailure(CommandError):
    """
    Base error that is raised when a check fails for a command. Anything raised by a check
    should inherit from this class.
    """

    def __init__(self, text: typing.Optional[str] = None) -> None:
        self.text: typing.Optional[str] = text
        """The error text."""


class OnlyInGuild(CheckFailure):
    """
    Error raised when a command marked as guild only is attempted to be invoked in DMs.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class OnlyInDM(CheckFailure):
    """
    Error raised when a command marked as DM only is attempted to be invoked in a guild.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class NotOwner(CheckFailure):
    """
    Error raised when a command marked as owner only is attempted to be invoked by another user.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class BotOnly(CheckFailure):
    """
    Error raised when the command invoker is not a bot.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class WebhookOnly(CheckFailure):
    """
    Error raised when the command invoker is not a webhook.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class HumanOnly(CheckFailure):
    """
    Error raised when the command invoker is not an human.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class NSFWChannelOnly(CheckFailure):
    """
    Error raised when a command that must be invoked in an NSFW channel is attempted to be invoked outside of one.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class MissingRequiredRole(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more role required.
    """

    def __init__(self, text: str) -> None:
        self.text: str = text
        """The error text."""


class MissingRequiredPermission(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more permission required.
    """

    def __init__(self, text: str, permissions: hikari.Permissions) -> None:
        self.text: str = text
        """The error text."""
        self.permissions: hikari.Permissions = permissions
        """Permission(s) the bot is missing."""


class BotMissingRequiredPermission(CheckFailure):
    """
    Error raised when the bot is missing one or more permission required for the command to be run.
    """

    def __init__(self, text: str, permissions: hikari.Permissions) -> None:
        self.text: str = text
        """The error text."""
        self.permissions: hikari.Permissions = permissions
        """Permission(s) the bot is missing."""


class MissingRequiredAttachment(CheckFailure):
    """
    Error raised when the command invocation message is missing an attachment, or an
    attachment with the correct file extension.
    """

    def __init__(self, text) -> None:
        self.text: str = text
        """The error text."""


class CommandInvocationError(CommandError):
    """
    Error raised if an error is encountered during command invocation. This will only be raised
    if all the checks passed and an error was raised somewhere inside the command.
    This effectively acts as a wrapper for the original exception for easier handling in an error handler.
    """

    def __init__(self, text: str, original: Exception) -> None:
        self.text: str = text
        """The error text."""
        self.original: Exception = original
        """The original exception that caused this to be raised."""

    @property
    def __cause__(self) -> Exception:
        return self.original
