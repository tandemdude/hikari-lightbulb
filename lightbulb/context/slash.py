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

from lightbulb import commands
from lightbulb.context import base

if t.TYPE_CHECKING:
    from lightbulb import app as app_


class SlashContext(base.ApplicationContext):
    """
    An implementation of :obj:`~.context.base.Context` for slash commands.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the context is linked to.
        event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): The event to create the context
            from.
        command (:obj:`~.commands.slash.SlashCommand`): The command that the context is for.
    """

    __slots__ = ("_options", "_raw_options")

    def __init__(
        self, app: app_.BotApp, event: hikari.InteractionCreateEvent, command: commands.slash.SlashCommand
    ) -> None:
        super().__init__(app, event, command)
        self._options: t.Dict[str, t.Any] = {}
        self._raw_options: t.Sequence[hikari.CommandInteractionOption] = self.interaction.options or []
        self._parse_options(self.interaction.options)

    def _parse_options(self, options: t.Optional[t.Sequence[hikari.CommandInteractionOption]]) -> None:
        for opt in options or []:
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

        for opt in self.command.options.values():
            self._options.setdefault(opt.name, opt.default if opt.default is not hikari.UNDEFINED else None)

    @property
    def raw_options(self) -> t.Dict[str, t.Any]:
        return self._options

    @property
    def prefix(self) -> str:
        return "/"

    @property
    def command(self) -> commands.slash.SlashCommand:
        assert isinstance(self._command, commands.slash.SlashCommand)
        return self._command
