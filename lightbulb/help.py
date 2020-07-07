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
from __future__ import annotations
import typing
import inspect

from lightbulb import context
from lightbulb import commands
from lightbulb import plugins
from lightbulb import command_handler
from lightbulb import errors


async def get_help_text(
    object: typing.Union[commands.Command, commands.Group, plugins.Plugin]
) -> str:
    """
    Get the help text for a command, group or plugin, extracted from its docstring.

    Args:
        object (Union[ :obj:`~.commands.Command`, :obj:`~.commands.Group`, :obj:`~.plugins.Plugin` ]): The
            object to get the help text for.

    Returns:
        :obj:`str`: The extracted help text, or ``"No help text provided."`` if no help text has
        been provided for the object.
    """
    if not isinstance(object, plugins.Plugin):
        return inspect.getdoc(object._callback) or "No help text provided."
    else:
        doc = inspect.getdoc(object)
        return (
            doc if doc != inspect.getdoc(plugins.Plugin) else "No help text provided."
        )


@commands.command(name="help")
async def help_cmd(ctx):
    obj = ctx.message.content[len(f"{ctx.prefix}{ctx.invoked_with}") :].strip().split()
    await ctx.bot._help_impl.resolve_help_obj(ctx, obj)


class HelpCommand:
    """
    The default help command implementation. This class should be subclassed if you
    wish to customise the format or other aspects of the bot's help command.

    Args:
        bot (:obj:`~.command_handler.BotWithHandler`): Bot instance to add the help command class to.
    """

    def __init__(self, bot: command_handler.BotWithHandler) -> None:
        self.bot = bot
        self.bot.add_command(help_cmd)

    async def filter_commands(
        self,
        context: context.Context,
        command_list: typing.List[typing.Union[commands.Command, commands.Group]],
    ) -> typing.List[typing.Union[commands.Command, commands.Group]]:
        """
        Filter a list of :obj:`~.commands.Command` and :obj:`~.commands.Group`, removing any commands that cannot
        be run under the given context by running all checks for each command in turn.

        Args:
            context (:obj:`~.context.Context`): The context to filter the commands under.
            command_list (List[ Union[ :obj:`~.commands.Command`, :obj:`~.commands.Group` ] ]): List of commands to filter.

        Returns:
            List[ Union[ :obj:`~.commands.Command`, :obj:`~.commands.Group` ] ]: List containing filtered commands.
        """
        filtered_commands = []
        for command in command_list:
            try:
                await command.is_runnable(context)
                filtered_commands.append(command)
            except errors.CheckFailure:
                pass
        return filtered_commands

    async def get_command_signature(
        self, command: typing.Union[commands.Command, commands.Group]
    ) -> str:
        signature = inspect.signature(command._callback)
        items = [command.name]
        num_args = len(signature.parameters) - command._max_args
        for name, param in list(signature.parameters.items())[num_args:]:
            if param.default is param.empty:
                items.append(f"<{name}>")
            else:
                items.append(f"[{name}={param.default}]")
        return " ".join(items)

    async def resolve_help_obj(self, context, obj):
        if not obj:
            await self.send_help_overview(context)
        else:
            await context.reply(obj)

    async def send_help_overview(self, context: context.Context) -> None:
        await context.reply("This would be the help overview")

    async def send_plugin_help(
        self, context: context.Context, plugin: plugins.Plugin
    ) -> None:
        pass

    async def send_command_help(
        self, context: context.Context, command: commands.Command
    ) -> None:
        pass

    async def send_group_help(
        self, context: context.Context, group: commands.Group
    ) -> None:
        pass
