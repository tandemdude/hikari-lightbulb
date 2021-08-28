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

__all__: typing.Final[typing.List[str]] = ["SlashCommandContext"]

import typing

import hikari

if typing.TYPE_CHECKING:
    from lightbulb import command_handler
    from lightbulb.slash_commands import commands


class SlashCommandContext:
    """
    The context a slash command was invoked under.

    Args:
        bot (:obj:`~lightbulb.command_handler.Bot`): The bot instance that received the slash command.
        interaction (:obj:`hikari.CommandInteraction`): The interaction for this slash command invocation.
        command (:obj:`~lightbulb.slash_commands.SlashCommand`): The :obj:`~SlashCommand` object that was invoked.
    """

    __slots__: typing.Sequence[str] = ("bot", "_interaction", "_command", "options")

    def __init__(
        self,
        bot: command_handler.Bot,
        interaction: hikari.CommandInteraction,
        command: commands.TopLevelSlashCommandBase,
    ) -> None:
        self.bot = bot
        """The bot instance that received the slash command."""
        self._interaction = interaction
        self._command = command

        self.options: typing.Mapping[str, hikari.CommandOption] = (
            {option.name: option for option in self._interaction.options}
            if self._interaction.options is not None
            else {}
        )
        """A mapping of :obj:`str` option name to :obj:`hikari.CommandInteractionOption` containing the options the command was invoked with."""

    @property
    def interaction(self) -> hikari.CommandInteraction:
        """The interaction for this slash command invocation."""
        return self._interaction

    @property
    def channel_id(self) -> hikari.Snowflake:
        """The channel ID that the slash command was invoked in."""
        return self._interaction.channel_id

    @property
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        """The guild ID that the slash command was invoked in, or ``None`` if in DMs."""
        return self._interaction.guild_id

    @property
    def member(self) -> typing.Optional[hikari.Member]:
        """The :obj:`hikari.Member` object for the user that invoked the slash command, or ``None`` if in DMs."""
        return self._interaction.member

    @property
    def user(self) -> hikari.User:
        """The user object for the user that invoked the slash command."""
        return self._interaction.user

    @property
    def author(self) -> hikari.User:
        """Alias for :obj:`SlashCommandContext.user`."""
        return self.user

    @property
    def command_name(self) -> str:
        """The name of the slash command being invoked."""
        return self._interaction.command_name

    @property
    def command_id(self):
        """The ID of the slash command being invoked."""
        return self._interaction.command_id

    @property
    def command(self) -> hikari.Command:
        """The :obj:`hikari.Command` object for this specific context."""
        return self._command.get_command(self.guild_id)

    @property
    def channel(self) -> typing.Optional[hikari.GuildChannel]:
        """The cached channel that the command was invoked in, or ``None`` if not found."""
        return self._interaction.get_channel()

    @property
    def guild(self) -> typing.Optional[hikari.GatewayGuild]:
        """The cached guild that the command was invoked in, or ``None`` if not found."""
        return self.bot.cache.get_guild(self.guild_id)

    @property
    def resolved(self) -> typing.Optional[hikari.ResolvedOptionData]:
        """Mappings of the objects resolved for the provided command options."""
        return self._interaction.resolved

    async def respond(self, content: hikari.UndefinedType = hikari.UNDEFINED, **kwargs: hikari.UndefinedType) -> None:
        """
        Alias for :obj:`hikari.CommandInteraction.create_initial_response` but without having to pass
        in the ``response_type`` (it is set to :obj:`hikari.ResponseType.MESSAGE_CREATE`) See Hikari documentation
        for kwargs you can pass in.

        Args:
            content (:obj:`hikari.UndefinedType`): The message content, generally :obj:`str`.

        Returns:
            ``None``
        """
        await self._interaction.create_initial_response(hikari.ResponseType.MESSAGE_CREATE, content, **kwargs)

    async def edit_response(self, *args, **kwargs) -> None:
        """
        Alias for :obj:`hikari.CommandInteraction.edit_initial_response`. See Hikari documentation
        for args and kwargs you can pass in.

        Returns:
            ``None``
        """
        await self._interaction.edit_initial_response(*args, **kwargs)

    async def delete_response(self) -> None:
        """
        Alias for :obj:`hikari.CommandInteraction.delete_initial_response`.

        Returns:
            ``None``
        """
        await self._interaction.delete_initial_response()
