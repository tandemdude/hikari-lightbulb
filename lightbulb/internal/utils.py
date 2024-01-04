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

import dataclasses
import typing as t

from lightbulb.commands import commands
from lightbulb.commands import groups


@dataclasses.dataclass(kw_only=True, slots=True)
class CommandCollection:
    slash: t.Optional[t.Union[groups.Group, t.Type[commands.SlashCommand]]] = None
    user: t.Optional[t.Type[commands.UserCommand]] = None
    message: t.Optional[t.Type[commands.MessageCommand]] = None

    def put(
        self,
        command: t.Union[groups.Group, t.Type[commands.CommandBase]],
    ) -> None:
        if isinstance(command, groups.Group) or issubclass(command, commands.SlashCommand):
            self.slash = command
        elif issubclass(command, commands.UserCommand):
            self.user = command
        elif issubclass(command, commands.MessageCommand):
            self.message = command
        else:
            raise TypeError("unsupported command passed")
