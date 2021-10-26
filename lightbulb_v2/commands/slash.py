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

__all__ = ["SlashCommand"]

import typing as t

from lightbulb_v2.commands import base


class SlashCommand(base.ApplicationCommand):
    """
    An implementation of :obj:`~.commands.base.Command` representing a slash command.

    See the `API Documentation <https://discord.com/developers/docs/interactions/application-commands#slash-commands>`_.
    """

    def as_create_kwargs(self) -> t.Dict[str, t.Any]:
        sorted_opts = sorted(self.options.values(), key=lambda o: int(o.required), reverse=True)
        return {
            "name": self.name,
            "description": self.description,
            "options": [o.as_application_command_option() for o in sorted_opts],
        }
