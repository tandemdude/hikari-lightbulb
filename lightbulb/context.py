# -*- coding: utf-8 -*-
# Copyright © tandemdude 2023-present
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

import typing as t

import attr

if t.TYPE_CHECKING:
    import hikari

    from lightbulb import client as client_
    from lightbulb import commands


@attr.define(frozen=True, kw_only=True, slots=True)
class Context:
    client: client_.Client

    interaction: hikari.CommandInteraction
    options: t.Sequence[hikari.CommandInteractionOption]

    command: commands.CommandBase

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflake]:
        return self.interaction.guild_id

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self.interaction.channel_id

    @property
    def user(self) -> hikari.User:
        return self.interaction.user

    @property
    def member(self) -> t.Optional[hikari.InteractionMember]:
        return self.interaction.member

    @property
    def command_data(self) -> commands.CommandData:
        return self.command._.command_data
