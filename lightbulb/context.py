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

__all__: typing.Final[typing.List[str]] = ["Context"]

import datetime
import functools
import re
import typing

import hikari

if typing.TYPE_CHECKING:
    from lightbulb import command_handler
    from lightbulb import commands
    from lightbulb import plugins


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

    __slots__: typing.Sequence[str] = ("_bot", "_message", "_prefix", "_invoked_with", "_command")

    def __init__(
        self,
        bot: command_handler.Bot,
        message: hikari.Message,
        prefix: str,
        invoked_with: str,
        command: commands.Command,
    ) -> None:
        self._bot: command_handler.Bot = bot
        """The bot instance."""
        self._message: hikari.Message = message
        """The message that the context derived from."""
        self._prefix: str = prefix
        """The command prefix used."""
        self._invoked_with: str = invoked_with
        """The command name or alias used."""
        self._command: commands.Command = command
        """The command that was invoked."""

    # XXX: should this be deprecated and changed to `app` to be consistent
    # with the entire hikari API, and the lightbulb error event API?
    @property
    def bot(self) -> command_handler.Bot:
        return self._bot

    @property
    def message(self) -> hikari.Message:
        return self._message

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def invoked_with(self) -> str:
        return self._invoked_with

    @property
    def command(self) -> commands.Command:
        return self._command

    @property
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        """ID of the guild the command was invoked in, or None if the command was invoked in DMs."""
        return self._message.guild_id

    @property
    def channel_id(self) -> hikari.Snowflake:
        """ID of the channel the command was invoked in."""
        return self._message.channel_id

    @property
    def content(self) -> str:
        """Raw content of the invocation message."""
        return self._message.content

    @property
    def member(self) -> typing.Optional[hikari.Member]:
        """Optional member corresponding to the context author."""
        return self._message.member

    @property
    def message_id(self) -> hikari.Snowflake:
        """ID of the message that invoked the command."""
        return self._message.id

    @property
    def timestamp(self) -> datetime.datetime:
        """The timestamp the context message was sent at."""
        return self._message.timestamp

    @property
    def edited_timestamp(self) -> typing.Optional[datetime.datetime]:
        """Optional timestamp of the previous edit of the context message."""
        return self._message.edited_timestamp

    # XXX: these are at the time of writing typing.Sequence objects, but will
    # be refactored to use typing.AbstractSet as part of https://github.com/nekokatt/hikari/issues/273.
    @property
    def user_mentions(self) -> typing.Collection[hikari.Snowflake]:
        """The users mentioned in the context message."""
        return self._message.user_mentions

    @property
    def role_mentions(self) -> typing.Collection[hikari.Snowflake]:
        """The roles mentioned in the context message."""
        return self._message.role_mentions

    @property
    def channel_mentions(self) -> typing.Collection[hikari.Snowflake]:
        """The channels mentioned in the context message."""
        return self._message.channel_mentions

    @property
    def attachments(self) -> typing.Sequence[hikari.Attachment]:
        """The attachments to the context message."""
        return self._message.attachments

    @property
    def author(self) -> hikari.User:
        """The user who invoked the command."""
        return self._message.author

    @property
    def clean_prefix(self) -> str:
        """
        The context's prefix, cleaned to remove user mentions. If the bot is stateless, then this just
        returns the raw prefix.
        """

        def replace(match):
            user = self.bot.cache.get_user(hikari.Snowflake(match.group(1)))
            return f"@{user}" if user is not None else self.prefix

        return re.sub(r"<@!?(\d+)>", replace, self.prefix)

    @property
    def guild(self) -> typing.Optional[hikari.Guild]:
        """
        The cached :obj:`hikari.Guild` instance for the context's guild ID.

        This will be None if the bot is stateless, the guild is not found in the cache,
        or the context is for a command run in DMs.
        """
        if self.guild_id is not None:
            return self.bot.cache.get_available_guild(self.guild_id)
        return None

    @property
    def channel(self) -> typing.Optional[hikari.TextableChannel]:
        """
        The cached :obj:`hikari.TextableChannel` instance for the context's channel ID.

        This will be None if the bot is stateless, the channel is not found in the cache,
        or the context is for a command run in DMs.
        """
        if self.guild_id is not None:
            return self.bot.cache.get_guild_channel(self.channel_id)
        return None

    @functools.wraps(hikari.Message.respond)
    async def respond(self, *args, **kwargs) -> hikari.Message:
        """
        Alias for ``ctx.message.respond(...)``.
        Replies to the message in the current context.

        Args:
            *args: The positional arguments :meth:`hikari.messages.Message.respond` is invoked with
            **kwargs: The keyword arguments :meth:`hikari.messages.Message.respond` is invoked with
        """
        return await self.message.respond(*args, **kwargs)

    async def send_help(self, obj: typing.Union[commands.Command, plugins.Plugin] = None) -> None:
        """
        Send help for the given object or the bot's help overview if no object
        is supplied to the current context.

        Args:
            obj (Union[ :obj:`~.commands.Command`, :obj:`~.plugins.Plugin` ]): The object to send help for.
                Defaults to ``None``.

        Returns:
            ``None``
        """
        await self.bot.send_help(self, obj)
