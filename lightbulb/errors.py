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
from hikari.events import base

from lightbulb import context


class CommandErrorEvent(base.Event):
    """
    Event type to subscribe to for the processing of all command errors raised by the handler.

    Args:
        error (:obj:`.errors.CommandError`): An instance or subclass of ``CommandError``. The error that was raised.
        message (:obj:`hikari.models.messages.Message`): The message that caused the exception to be raised.

    Example:

        .. code-block:: python

            from lightbulb.errors import CommandErrorEvent

            bot = lightbulb.Bot(token="token_here", prefix="!")

            @bot.listen(CommandErrorEvent)
            async def handle_command_error(error):
                ...

    """

    def __init__(self, error, message) -> None:
        self.error = error
        self.message = message


class ExtensionError(Exception):
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


class CommandError(Exception):
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


class UnclosedQuotes(CommandError):
    """
    Error raised when no closing quote is found for a quoted argument.

    Args:
        text (:obj:`str`): The text that caused the error to be raised.
    """

    def __init__(self, text: str) -> None:
        self.text = text


class CheckFailure(CommandError):
    """
    Base error that is raised when a check fails for a command. Anything raised by a check
    should inherit from this class.

    Args:
        context (:obj:`.context.Context`): The context that caused the check to fail.
    """

    def __init__(self, context: context.Context) -> None:
        self.context = context


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
