# -*- coding: utf-8 -*-
# Copyright © tandemdude 2020-present
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

__all__ = ["SlashContext"]

import typing as t

import hikari

from lightbulb_v2 import commands
from lightbulb_v2.context import base

if t.TYPE_CHECKING:
    from lightbulb_v2 import app as app_


class SlashContext(base.Context):
    """
    An implementation of :obj:`~.context.base.Context` for prefix commands.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the context is linked to.
        event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): The event to create the context
            from.
        command (:obj:`~.commands.slash.SlashCommand`): The command that the context is for.
    """

    __slots__ = ("_event", "_interaction", "_command", "initial_response_sent", "_options")

    def __init__(
        self, app: app_.BotApp, event: hikari.InteractionCreateEvent, command: commands.slash.SlashCommand
    ) -> None:
        super().__init__(app)
        self._event = event
        assert isinstance(event.interaction, hikari.CommandInteraction)
        self._interaction: hikari.CommandInteraction = event.interaction
        self._command = command

        self._options: t.Dict[str, t.Any] = {}
        for opt in (self._interaction.options or []):
            # Why is mypy so annoying about this ??
            if opt.type is hikari.OptionType.USER and self.resolved is not None:
                val = t.cast(hikari.Snowflake, opt.value)
                self._options[opt.name] = self.resolved.members.get(val, self.resolved.users.get(val, opt.value))
            elif opt.type is hikari.OptionType.CHANNEL and self.resolved is not None:
                val = t.cast(hikari.Snowflake, opt.value)
                self._options[opt.name] = self.resolved.channels.get(val, opt.value)
            elif opt.type is hikari.OptionType.ROLE and self.resolved is not None:
                val = t.cast(hikari.Snowflake, opt.value)
                self._options[opt.name] = self.resolved.roles.get(val, opt.value)
            else:
                self._options[opt.name] = opt.value

        self.initial_response_sent: bool = False
        """Whether or not the initial response has been sent for this interaction."""

    @property
    def event(self) -> hikari.InteractionCreateEvent:
        return self._event

    @property
    def raw_options(self) -> t.Dict[str, t.Any]:
        return self._options

    @property
    def interaction(self) -> hikari.CommandInteraction:
        return self._interaction

    @property
    def channel_id(self) -> hikari.Snowflakeish:
        return self._interaction.channel_id

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflakeish]:
        return self._interaction.guild_id

    @property
    def member(self) -> t.Optional[hikari.Member]:
        return self._interaction.member

    @property
    def author(self) -> hikari.User:
        return self._interaction.user

    @property
    def invoked_with(self) -> str:
        return self._command.name

    @property
    def prefix(self) -> str:
        return "/"

    @property
    def command(self) -> commands.base.Command:
        return self._command

    @property
    def command_id(self) -> hikari.Snowflake:
        return self._interaction.command_id

    @property
    def resolved(self) -> t.Optional[hikari.ResolvedOptionData]:
        return self._interaction.resolved

    def get_channel(self) -> t.Optional[t.Union[hikari.GuildChannel, hikari.Snowflake]]:
        if self.guild_id is not None:
            return self.app.cache.get_guild_channel(self.channel_id)
        return self.app.cache.get_dm_channel_id(self.user)

    async def respond(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        """
        Create a response for this context. The first time this method is called, the initial
        interaction response will be created by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.create_initial_response` with the response
        type set to :obj:`~hikari.interactions.base_interactions.ResponseType.MESSAGE_CREATE` if not otherwise
        specified.

        Subsequent calls will instead create followup responses to the interaction by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.execute`.

        Args:
            *args (Any): Positional arguments passed to ``CommandInteraction.create_initial_response`` or
                ``CommandInteraction.execute``.
            **kwargs: Keyword arguments passed to ``CommandInteraction.create_initial_response`` or
                ``CommandInteraction.execute``.

        Returns:
            :obj:`~hikari.messages.Message`: The created message object.
        """
        if self.initial_response_sent:
            return await self._interaction.execute(*args, **kwargs)

        if args and not isinstance(args[0], hikari.ResponseType):
            kwargs.setdefault("response_type", hikari.ResponseType.MESSAGE_CREATE)
        await self._interaction.create_initial_response(*args, **kwargs)
        return await self._interaction.fetch_initial_response()
