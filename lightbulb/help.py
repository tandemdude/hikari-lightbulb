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

__all__: typing.Final[typing.Tuple[str]] = [
    "get_help_text",
    "get_command_signature",
    "filter_commands",
    "HelpCommand",
]

import inspect
import typing

from lightbulb import commands
from lightbulb import errors
from lightbulb import plugins
from lightbulb import utils

if typing.TYPE_CHECKING:
    from lightbulb import command_handler
    from lightbulb import context


def get_help_text(object: typing.Union[commands.Command, plugins.Plugin]) -> str:
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


def get_command_signature(command: commands.Command) -> str:
    """
    Get the command signature (usage) for a command or command group.
    The signature is returned in the format:
    ``<command name> <required arg> [optional arg]``

    Args:
        command (:obj:`~.commands.Command`): The command or group to get the signature for.

    Returns:
        :obj:`str`: Signature for the command.
    """
    signature = inspect.signature(command._callback)

    command_qualname = []
    cmd = command
    while cmd is not None:
        command_qualname.append(cmd.name)
        cmd = cmd.parent
    command_qualname = " ".join(command_qualname[::-1])

    items = [command_qualname]
    num_args = len(signature.parameters) - command.arg_details.max_args
    for name, param in list(signature.parameters.items())[num_args:]:
        if param.default is param.empty:
            items.append(f"<{name}>")
        else:
            items.append(f"[{name}={param.default}]")
    return " ".join(items)


async def filter_commands(
    context: context.Context, command_list: typing.Iterable[commands.Command],
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
        if command.hidden:
            continue
        try:
            await command.is_runnable(context)
            filtered_commands.add(command)
        except errors.CheckFailure:
            pass
    return list(filtered_commands)


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
        bot (:obj:`~.command_handler.Bot`): Bot instance to add the help command class to.
    """

    def __init__(self, bot: command_handler.Bot) -> None:
        self.bot = bot
        if self.bot.get_command("help") is None:
            self.bot.add_command(_help_cmd)

    @staticmethod
    async def send_paginated_help(text: typing.Sequence[str], context: context.Context) -> None:
        """
        Paginate the help text using :obj:`~.utils.pag.StringPaginator` and send each
        of the created pages to the context in order. Note that by default, only the
        help overview is paginated as this is the most likely to exceed the 2000
        character message limit.

        Args:
            text (Sequence[ :obj:`str` ]): A sequence of text to be paginated.
            context (:obj:`~.context.Context`): The context to send the help to.

        Returns:
            ``None``
        """
        pag = utils.pag.StringPaginator()
        for line in text:
            pag.add_line(line)
        for page in pag.build_pages():
            await context.reply(page)

    async def resolve_help_obj(self, context: context.Context, obj: typing.List[str]) -> None:
        """
        Resolve the object to send help information for from the
        arguments passed to the help command.

        Args:
            context (:obj:`~.context.Context`): Context to send the help to.
            obj (List[ :obj:`str` ]): Arguments supplied to the help command.

        Returns:
            ``None``
        """
        if not obj:
            await self.send_help_overview(context)
        elif len(obj) == 1:
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
                    await self.object_not_found(context, obj[0])
        else:
            if (plugin := self.bot.get_plugin(" ".join(obj))) is not None:
                await self.send_plugin_help(context, plugin)
                return

            command = self.bot.get_command(obj[0])

            next_obj = 1
            while isinstance(command, commands.Group):
                try:
                    command = command.get_subcommand(obj[next_obj])
                    next_obj += 1
                except IndexError:
                    break

            if isinstance(command, commands.Group):
                await self.send_group_help(context, command)
            elif isinstance(command, commands.Command):
                await self.send_command_help(context, command)
            else:
                await self.object_not_found(context, " ".join(obj))

    async def object_not_found(self, context: context.Context, name: str) -> None:
        """
        Method called when help is requested for an object that does not exist.

        Args:
            context (:obj:`~.context.Context`): Context to send the error message to.
            name (:obj:`str`): The name of the object that help was requested for.

        Returns:
            ``None``
        """
        await context.reply(f"`{name}` is not a valid command, group or category.")

    async def send_help_overview(self, context: context.Context) -> None:
        """
        Method called when the help command is run without any arguments.

        Args:
            context (:obj:`~.context.Context`): Context to send the help to.

        Returns:
            ``None``
        """
        plugin_commands = [
            [plugin.name, await filter_commands(context, plugin.commands.values())]
            for plugin in self.bot.plugins.values()
        ]
        all_plugin_commands = []
        for _, cmds in plugin_commands:
            all_plugin_commands.extend(cmds)
        uncategorised_commands = await filter_commands(context, self.bot.commands.difference(set(all_plugin_commands)))
        plugin_commands.insert(0, ["Uncategorised", uncategorised_commands])

        help_text = ["> __**Bot help**__\n"]
        for plugin, commands in plugin_commands:
            if not commands:
                continue
            help_text.append(f"> **{plugin}**")
            for c in sorted(commands, key=lambda c: c.name):
                short_help = get_help_text(c).split("\n")[0]
                help_text.append(f"> • `{c.name}` - {short_help}")
        help_text.append(f"> \n> Use `{context.prefix}help [command]` for more information.")
        await self.send_paginated_help(help_text, context)

    async def send_plugin_help(self, context: context.Context, plugin: plugins.Plugin) -> None:
        """
        Method called when the help command is run with an argument that
        resolves into the name of a plugin.

        Args:
            context (:obj:`~.context.Context`): Context to send the help to.
            plugin (:obj:`~.plugins.Plugin`): Plugin object to send help for.

        Returns:
            ``None``
        """
        help_text = [
            f"> **Help for category `{plugin.name}`**",
            get_help_text(plugin) or "No help text provided.",
            f"Commands:",
            ", ".join(f"`{c.name}`" for c in sorted(plugin.commands.values(), key=lambda c: c.name))
            or "No commands in the category",
        ]
        await context.reply("\n> ".join(help_text))

    async def send_command_help(self, context: context.Context, command: commands.Command) -> None:
        """
        Method called when the help command is run with an argument that
        resolves into the name of a registered command.

        Args:
            context (:obj:`~.context.Context`): Context to send the help to.
            command (:obj:`~.commands.Command`): Command object to send help for.

        Returns:
            ``None``
        """
        help_text = [
            f">**Help for command `{command.name}`**",
            f"Usage:",
            f"```{context.prefix}{get_command_signature(command)}```",
            get_help_text(command) or "No help text provided.",
        ]
        await context.reply("\n>".join(help_text))

    async def send_group_help(self, context: context.Context, group: commands.Group) -> None:
        """
        Method called when the help command is run with an argument that
        resolves into the name of a registered command group.

        Args:
            context (:obj:`~.context.Context`): Context to send the help to.
            command (:obj:`~.commands.Group`): Group object to send help for.

        Returns:
            ``None``
        """
        help_text = [
            f"> **Help for command group `{group.name}`**",
            "Usage:",
            f"```{context.prefix}{get_command_signature(group)}```",
            get_help_text(group) or "No help text provided.",
            f"Subcommands:" ", ".join(f"`{c.name}`" for c in sorted(group.subcommands, key=lambda c: c.name))
            or "No subcommands in the group",
        ]
        await context.reply("\n>".join(help_text))
