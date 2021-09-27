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

__all__: typing.Final[typing.List[str]] = ["SlashCommandOptionsWrapper", "SlashCommandContext"]

import functools
import typing
import warnings

import hikari

if typing.TYPE_CHECKING:
    from lightbulb import command_handler
    from lightbulb.slash_commands import commands


class SlashCommandOptionsWrapper:
    """
    A wrapper class for :obj:`~lightbulb.slash_commands.SlashCommandContext.options` which allows the user
    to access the option values through a more user_friendly, attribute syntax.
    :obj:`~lightbulb.slash_commands.SlashCommandOptionsWrapper.option_name` will return either the option's value,
    or ``None`` if the option was not provided in the slash command invocation.

    This is accessible through :obj:`~lightbulb.slash_commands.SlashCommandContext.option_values`

    Args:
        options (Mapping[:obj:`str`, :obj:`hikari.CommandInteractionOption`): The options that the slash command
            was called with.
        defaults (Mapping[:obj:`str`, Any]): The default values for the slash command options.
    """

    __slots__: typing.Sequence[str] = ("_options", "_defaults")

    def __init__(
        self, options: typing.Mapping[str, hikari.CommandInteractionOption], defaults: typing.Mapping[str, typing.Any]
    ) -> None:
        self._options = options
        self._defaults = defaults

    def __getattr__(self, item: str) -> typing.Optional[typing.Union[str, int, bool, float]]:
        option = self._options.get(item)
        return option.value if option is not None else self._defaults.get(item)


class SlashCommandContext:
    """
    The context a slash command was invoked under.

    Args:
        bot (:obj:`~lightbulb.command_handler.Bot`): The bot instance that received the slash command.
        interaction (:obj:`hikari.CommandInteraction`): The interaction for this slash command invocation.
        command (:obj:`~lightbulb.slash_commands.SlashCommand`): The :obj:`~SlashCommand` object that was invoked.
    """

    def __init__(
        self,
        bot: command_handler.Bot,
        interaction: hikari.CommandInteraction,
        command: commands.BaseSlashCommand,
    ) -> None:
        self.bot = bot
        """The bot instance that received the slash command."""
        self._interaction = interaction
        self._command = command

        self._options: typing.Mapping[str, hikari.CommandInteractionOption] = (
            {option.name: option for option in self._interaction.options}
            if self._interaction.options is not None
            else {}
        )

        self.initial_response_sent = False
        """Whether or not an initial response has been sent for the interaction."""

    @property
    def raw_options(self) -> typing.Mapping[str, hikari.CommandInteractionOption]:
        """
        A mapping of :obj:`str` option name to :obj:`hikari.CommandInteractionOption`
        containing the options the command was invoked with.
        """
        return self._options

    @functools.cached_property
    def options(self) -> SlashCommandOptionsWrapper:
        """
        The values for the slash command's various options.

        Returns:
            :obj:`~SlashCommandOptionsWrapper`
        """
        return SlashCommandOptionsWrapper(self._options, self._command._defaults)

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
    def member(self) -> typing.Optional[hikari.InteractionMember]:
        """
        The :obj:`hikari.InteractionMember` object for the user that invoked the slash
        command, or ``None`` if in DMs.
        """
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

    def get_channel(self) -> typing.Optional[hikari.GuildChannel]:
        """The cached channel that the command was invoked in, or ``None`` if not found."""
        return self._interaction.get_channel()

    def get_guild(self) -> typing.Optional[hikari.GatewayGuild]:
        """The cached guild that the command was invoked in, or ``None`` if not found."""
        return self.bot.cache.get_guild(self.guild_id)

    @property
    def resolved(self) -> typing.Optional[hikari.ResolvedOptionData]:
        """Mappings of the objects resolved for the provided command options."""
        return self._interaction.resolved

    async def respond(
        self, content: hikari.UndefinedType = hikari.UNDEFINED, **kwargs: hikari.UndefinedType
    ) -> typing.Optional[hikari.Message]:
        """
        Alias for :obj:`hikari.CommandInteraction.create_initial_response` but without having to pass
        in the ``response_type`` (it is set to :obj:`hikari.ResponseType.MESSAGE_CREATE`) See Hikari documentation
        for kwargs you can pass in. You can override the response type if you want to by setting
        the kwarg ``response_type`` manually.

        Args:
            content (:obj:`hikari.UndefinedType`): The message content, generally :obj:`str`.

        Keyword Args:
            **kwargs: Kwargs passed to :obj:`hikari.CommandInteraction.create_initial_response`
                or :obj:`hikari.CommandInteraction.execute` if you have already responded
                to the interaction using this method.

        Returns:
            Optional[ :obj:`hikari.Message` ]

        Note:
            This will be a shortcut to :obj:`~lightbulb.slash_commands.SlashCommandContext.followup`
            if you have already responded to the interaction using this method.
        """
        if self.initial_response_sent:
            return await self.followup(content, **kwargs)

        resp_type = kwargs.pop("response_type", hikari.ResponseType.MESSAGE_CREATE)
        await self._interaction.create_initial_response(resp_type, content, **kwargs)
        self.initial_response_sent = True

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

    @functools.wraps(hikari.CommandInteraction.execute)
    async def followup(self, *args, **kwargs) -> hikari.Message:
        """
        Alias for :obj:`hikari.CommandInteraction.execute`. Allows you to create followup responses for
        the interaction.

        Args:
            *args: Args passed to :obj:`hikari.CommandInteraction.execute`
            **kwargs: Kwargs passed to :obj:`hikari.CommandInteraction.execute`

        Returns:
            :obj:`hikari.Message`: The response message created.
        """
        return await self._interaction.execute(*args, **kwargs)
