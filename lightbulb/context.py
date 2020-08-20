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

__all__: typing.Final[typing.List[str]] = ["Context"]

import datetime
import typing

import hikari

if typing.TYPE_CHECKING:
    from lightbulb import command_handler
    from lightbulb import commands


class Context:
    """
    The context a command was invoked under.

    Args:
        bot (:obj:`~.command_handler.Bot`): The bot instance that received the command.
        message (:obj:`hikari.messages.Message`): The message the context was created from.
        prefix (:obj:`str`): The prefix used in the context.
        invoked_with (:obj:`str`): The name or alias used to invoke a command.
        command (:obj:`~.commands.Command`): The command that was invoked.

    Note:
        For information on types for the various properties see :obj:`hikari.messages.Message`.
    """

    def __init__(
        self,
        bot: command_handler.Bot,
        message: hikari.Message,
        prefix: str,
        invoked_with: str,
        command: commands.Command,
    ) -> None:
        self.bot: command_handler.Bot = bot
        """The bot instance."""
        self.message: hikari.Message = message
        """The message that the context derived from."""
        self.prefix: str = prefix
        """The command prefix used."""
        self.invoked_with: str = invoked_with
        """The command name or alias used."""
        self.command: commands.Command = command
        """The command that was invoked."""

    guild_id: typing.Optional[hikari.Snowflake] = property(lambda self: self.message.guild_id)
    """Optional ID of the guild the command was invoked in."""
    channel_id: hikari.Snowflake = property(lambda self: self.message.channel_id)
    """ID of the channel the command was invoked in."""
    content: str = property(lambda self: self.message.content)
    """Raw content of the invocation message."""
    member: typing.Optional[hikari.Member] = property(lambda self: self.message.member)
    """Optional member corresponding to the context author."""
    message_id: hikari.Snowflake = property(lambda self: self.message.id)
    """ID of the message that invoked the command."""
    timestamp: datetime.datetime = property(lambda self: self.message.timestamp)
    """The timestamp the context message was sent at."""
    edited_timestamp: typing.Optional[datetime.datetime] = property(lambda self: self.message.edited_timestamp)
    """Optional timestamp of the previous edit of the context message."""
    user_mentions: typing.Collection[hikari.Snowflake] = property(lambda self: self.message.user_mentions)
    """The users mentioned in the context message."""
    role_mentions: typing.Collection[hikari.Snowflake] = property(lambda self: self.message.role_mentions)
    """The roles mentioned in the context message."""
    channel_mentions: typing.Collection[hikari.Snowflake] = property(lambda self: self.message.channel_mentions)
    """The channels mentioned in the context message."""
    attachments: typing.Sequence[hikari.Attachment] = property(lambda self: self.message.attachments)
    """The attachments to the context message."""
    author: hikari.User = property(lambda self: self.message.author)
    """The user who invoked the command."""

    async def reply(self, *args, **kwargs) -> hikari.Message:
        """
        Alias for ``ctx.message.reply(...)``.
        Replies to the message in the current context.

        Args:
            *args: The positional arguments :meth:`hikari.messages.Message.reply` is invoked with
            **kwargs: The keyword arguments :meth:`hikari.messages.Message.reply` is invoked with
        """
        return await self.message.reply(*args, **kwargs)
