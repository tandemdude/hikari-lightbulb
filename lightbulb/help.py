# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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
import typing

from lightbulb import context
from lightbulb import commands
from lightbulb import plugins
from lightbulb import command_handler


class BasicHelpCommand:
    def __init__(self, bot: command_handler.BotWithHandler) -> None:
        self.bot = bot

    async def filter_commands(self, context: context.Context, command_list: typing.List[typing.Union[commands.Command, commands.Group]]) -> typing.List[typing.Union[commands.Command, commands.Group]]:
        """
        Filter a list of :obj:`~.commands.Command` and :obj:`~.commands.Group`, removing any commands that cannot
        be run under the given context by running all checks for each command in turn.

        Args:
            context (:obj:`~.context.Context`): The context to filter the commands under.
            command_list (List[ Union[ :obj:`~.commands.Command`, :obj:`~.commands.Group` ] ]): List of commands to filter.

        Returns:
            List[ Union[ :obj:`~.commands.Command`, :obj:`~.commands.Group` ] ]: List containing filtered commands.
        """
        pass

    async def send_help_overview(self, context: context.Context) -> None:
        pass

    async def send_plugin_help(self, context: context.Context, plugin: plugins.Plugin) -> None:
        pass

    async def send_command_help(self, context: context.Context, command: commands.Command) -> None:
        pass

    async def send_group_help(self, context: context.Context, group: commands.Group) -> None:
        pass
