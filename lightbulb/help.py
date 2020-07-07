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


def get_help_text(
    object: typing.Union[commands.Command, commands.Group, plugins.Plugin]
) -> str:
    """
    Get the help text for a command, group or plugin, extracted from its docstring.

    Args:
        object (Union[ :obj:`~.commands.Command`, :obj:`~.commands.Group`, :obj:`~.plugins.Plugin` ]): The
            object to get the help text for.

    Returns:
        :obj:`str`: The extracted help text, or an empty string if no help text has
        been provided for the object.
    """
    if not isinstance(object, plugins.Plugin):
        doc = inspect.getdoc(object._callback)
        return doc if doc is not None else ""
    else:
        doc = inspect.getdoc(object)
        return doc if doc != inspect.getdoc(plugins.Plugin) else ""


@commands.command(name="help")
async def _help_cmd(ctx):
    """
    Displays help for the bot, a command, or a category.
    If no object is specified with the command then a help menu
    for the bot as a whole is displayed instead.
    """
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
        if self.bot.get_command("help") is None:
            self.bot.add_command(_help_cmd)

    async def filter_commands(
        self, context: context.Context, command_list: typing.List[commands.Command],
    ) -> typing.List[commands.Command]:
        """
        Filter a list of :obj:`~.commands.Command` and :obj:`~.commands.Group`, removing any commands that cannot
        be run under the given context by running all checks for each command in turn.

        Args:
            context (:obj:`~.context.Context`): The context to filter the commands under.
            command_list (List[ :obj:`~.commands.Command` ]): List of commands to filter.

        Returns:
            List[ :obj:`~.commands.Command` ]: List containing filtered commands.
        """
        filtered_commands = set()
        for command in command_list:
            try:
                await command.is_runnable(context)
                filtered_commands.add(command)
            except errors.CheckFailure:
                pass
        return list(filtered_commands)

    def get_command_signature(
        self, command: typing.Union[commands.Command, commands.Group]
    ) -> str:
        signature = inspect.signature(command._callback)
        items = [command.name]
        num_args = len(signature.parameters) - command.arg_details.max_args
        for name, param in list(signature.parameters.items())[num_args:]:
            if param.default is param.empty:
                items.append(f"<{name}>")
            else:
                items.append(f"[{name}={param.default}]")
        return " ".join(items)

    async def resolve_help_obj(self, context, obj):
        if not obj:
            await self.send_help_overview(context)
        if len(obj) == 1:
            command = self.bot.get_command(obj[0])
            if isinstance(command, commands.Group):
                await self.send_group_help(context, command)
            elif isinstance(command, commands.Command):
                await self.send_command_help(context, command)
            else:
                plugin = self.bot.get_plugin(obj[0])
                if plugin is not None:
                    await self.send_plugin_help(context, plugin)
                else:
                    await self.entity_not_found(context, obj[0])

    async def entity_not_found(self, context, name):
        await context.reply(f"`{name}` is not a valid command, group or category.")

    async def send_help_overview(self, context: context.Context) -> None:
        plugin_commands = [
            [plugin.name, await self.filter_commands(context, plugin.commands.values())]
            for plugin in self.bot.plugins.values()
        ]
        all_plugin_commands = []
        for _, cmds in plugin_commands:
            all_plugin_commands.extend(cmds)
        uncategorised_commands = await self.filter_commands(
            context,
            list(set(self.bot.commands.values()).difference(set(all_plugin_commands))),
        )
        plugin_commands.append(["Uncategorised", uncategorised_commands])

        help_text = ["__**Bot help**__\n"]
        for plugin, commands in plugin_commands:
            if not commands:
                continue
            help_text.append(f"**{plugin}**")
            for c in commands:
                short_help = get_help_text(c).split("\n")[0]
                help_text.append(f"• `{c.name}` - {short_help}")
        help_text.append(
            f"\nUse `{context.prefix}help [command]` for more information."
        )
        await context.reply("\n".join(help_text))

    async def send_plugin_help(
        self, context: context.Context, plugin: plugins.Plugin
    ) -> None:
        await context.reply("This would be plugin help.")

    async def send_command_help(
        self, context: context.Context, command: commands.Command
    ) -> None:
        help_text = [
            f"**Help for command `{command.name}`**",
            "Usage:",
            f"```{context.prefix}{self.get_command_signature(command)}```",
            get_help_text(command),
        ]
        await context.reply("\n".join(help_text))

    async def send_group_help(
        self, context: context.Context, group: commands.Group
    ) -> None:
        await context.reply("This would be group help.")
