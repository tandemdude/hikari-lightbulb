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

import typing

if typing.TYPE_CHECKING:
    from hikari.models import messages
    from hikari.models import users

    from lightbulb import commands
    from lightbulb import command_handler


class Context:
    """
    The context a command was invoked under.

    Args:
        bot (:obj:`.command_handler.BotWithHandler`): The bot instance that received the command.
        message (:obj:`hikari.models.messages.Message`): The message the context was created from.
        prefix (:obj:`str`): The prefix used in the context.
        invoked_with (:obj:`str`): The name or alias used to invoke a command.
        command (:obj:`.commands.Command`): The command that was invoked.
    """

    def __init__(
        self,
        bot: command_handler.BotWithHandler,
        message: messages.Message,
        prefix: str,
        invoked_with: str,
        command: commands.Command,
    ) -> None:
        self.bot = bot
        self.message: messages.Message = message
        self.author: users.User = message.author
        self.prefix: str = prefix
        self.invoked_with: str = invoked_with
        self.command: commands.Command = command

    async def reply(self, *args, **kwargs) -> messages.Message:
        """
        Alias for ctx.message.reply(...).
        Replies to the message in the current context.

        Args:
            *args: The positional arguments :meth:`hikari.models.messages.Message.reply` is invoked with
            **kwargs: The keyword arguments :meth:`hikari.models.messages.Message.reply` is invoked with
        """
        return await self.message.reply(*args, **kwargs)
