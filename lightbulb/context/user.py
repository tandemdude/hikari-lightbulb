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

__all__ = ["UserContext"]

import typing as t

import hikari

from lightbulb import commands
from lightbulb.context import base

if t.TYPE_CHECKING:
    from lightbulb import app as app_


class UserContext(base.ApplicationContext):
    __slots__ = ("_options",)

    def __init__(
        self, app: app_.BotApp, event: hikari.InteractionCreateEvent, command: commands.user.UserCommand
    ) -> None:
        super().__init__(app, event, command)
        assert self.resolved is not None
        assert self.interaction.target_id is not None
        self._options = {
            "target": self.resolved.members.get(self.interaction.target_id)
            or self.resolved.users.get(self.interaction.target_id)
        }

    @property
    def raw_options(self) -> t.Dict[str, t.Any]:
        return self._options

    @property
    def command(self) -> commands.user.UserCommand:
        assert isinstance(self._command, commands.user.UserCommand)
        return self._command

    @property
    def prefix(self) -> str:
        return "\N{THREE BUTTON MOUSE}\N{VARIATION SELECTOR-16}"
