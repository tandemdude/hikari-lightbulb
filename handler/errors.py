# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
#
# This file is part of Hikari Command Handler.
#
# Hikari Command Handler is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari Command Handler is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari Command Handler. If not, see <https://www.gnu.org/licenses/>.
from hikari.events import base


class CommandErrorEvent(base.Event):
    """
    Event type to subscribe to for the processing of all command errors raised by the handler.

    Args:
        error (:obj:`.errors.CommandError`): An instance or subclass of ``CommandError``. The error that was raised.
        message (:obj:`hikari.models.messages.Message`): The message that caused the exception to be raised.

    Example:

        .. code-block:: python

            from handler.errors import CommandErrorEvent

            bot = handler.Bot(token="token_here", prefix="!")

            @bot.listen(CommandErrorEvent)
            async def handle_command_error(error):

    """

    def __init__(self, error, message) -> None:
        self.error = error
        self.message = message


class CommandError(Exception):
    """Base exception for the command handler."""

    pass


class CommandNotFound(CommandError):
    """
    Exception raised when a command when attempted to be invoked but one with that name could not be found.

    Args:
        invoked_with (:obj:`str`): The command string that was attempted to be invoked.
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
