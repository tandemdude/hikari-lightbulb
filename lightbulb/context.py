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

    Note:
        For information on types for the various properties see :obj:`hikari.models.messages.Message`.
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

    guild_id = property(lambda self: self.message.guild_id)
    """Optional ID of the guild the command was invoked in."""
    channel_id = property(lambda self: self.message.channel_id)
    """ID of the channel the command was invoked in."""
    content = property(lambda self: self.message.content)
    """Raw content of the invocation message."""
    member = property(lambda self: self.message.member)
    """Optional member corresponding to the context author."""
    message_id = property(lambda self: self.message.id)
    """ID of the message that invoked the command."""
    timestamp = property(lambda self: self.message.timestamp)
    """The timestamp the context message was sent at."""
    edited_timestamp = property(lambda self: self.message.edited_timestamp)
    """Optional timestamp of the previous edit of the context message."""
    user_mentions = property(lambda self: self.message.user_mentions)
    """The users mentioned in the context message."""
    role_mentions = property(lambda self: self.message.role_mentions)
    """The roles mentioned in the context message."""
    channel_mentions = property(lambda self: self.message.channel_mentions)
    """The channels mentioned in the context message."""
    attachments = property(lambda self: self.message.attachments)
    """The attachments to the context message."""

    async def reply(self, *args, **kwargs) -> messages.Message:
        """
        Alias for ctx.message.reply(...).
        Replies to the message in the current context.

        Args:
            *args: The positional arguments :meth:`hikari.models.messages.Message.reply` is invoked with
            **kwargs: The keyword arguments :meth:`hikari.models.messages.Message.reply` is invoked with
        """
        return await self.message.reply(*args, **kwargs)
