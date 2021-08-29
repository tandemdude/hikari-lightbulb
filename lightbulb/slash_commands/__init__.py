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
"""
.. error::
    The implementation of slash commands within a Plugin class is not supported.
"""
import typing

from lightbulb.slash_commands.commands import *
from lightbulb.slash_commands.context import *

__all__: typing.Final[typing.List[str]] = [
    "SlashCommandBase",
    "TopLevelSlashCommandBase",
    "SlashCommand",
    "SlashCommandGroup",
    "SlashSubGroup",
    "SlashSubCommand",
    "SlashCommandOptionsWrapper",
    "SlashCommandContext",
]
