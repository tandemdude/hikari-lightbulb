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

__all__ = ["BaseHelpCommand", "DefaultHelpCommand", "filter_commands"]

import abc
import collections
import typing as t

from lightbulb import commands
from lightbulb import errors
from lightbulb.utils import nav

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb import context as context_
    from lightbulb import plugins


async def filter_commands(
    cmds: t.Sequence[commands.base.Command], context: context_.base.Context
) -> t.Sequence[commands.base.Command]:
    """
    Evaluates the checks for each command provided, removing any that the checks fail for. This effectively
    removes any commands from the given collection that could not be invoked under the given context. This will
    also remove any commands with the ``hidden`` attribute set to ``True``.

    Args:
        cmds (Sequence[:obj:`~.commands.base.Command`]): Commands to filter.
        context (:obj:`~.context.base.Context`): Context to filter the commands under.

    Returns:
        Sequence[:obj:`~.commands.base.Command`]: Filtered commands.
    """
    new_cmds = []
    for cmd in cmds:
        if cmd.hidden:
            continue
        try:
            await cmd.evaluate_checks(context)
        except errors.CheckFailure:
            continue
        new_cmds.append(cmd)
    return new_cmds


class BaseHelpCommand(abc.ABC):
    """
    Base class for auto-generated help commands.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the help command is registered to.
    """

    __slots__ = ("app",)

    def __init__(self, app: app_.BotApp) -> None:
        self.app: app_.BotApp = app
        """The ``BotApp`` instance the help command is registered to."""

    @property
    def bot(self) -> t.Optional[app_.BotApp]:
        """Alias for :obj:`~BaseHelpCommand.app`"""
        return self.app

    async def send_help(self, context: context_.base.Context, obj: t.Optional[str]) -> None:
        """
        Resolve the given object and send the help text for it to the given context.

        Help resolution order:

        - Prefix command
        - Slash command
        - Message command
        - User command
        - Plugin

        Args:
            context (:obj:`~.context.base.Context`): Context to send help to.
            obj (:obj:`str`): String representation of the object to send help for.
        """
        await self._send_help(context, obj)

    async def _send_help(self, context: context_.base.Context, obj: t.Optional[str]) -> None:
        if obj is None:
            await self.send_bot_help(context)
            return

        p_cmd = self.app.get_prefix_command(obj)
        if p_cmd is not None and not p_cmd.hidden:
            if isinstance(p_cmd, (commands.prefix.PrefixCommandGroup, commands.prefix.PrefixSubGroup)):
                await self.send_group_help(context, p_cmd)
                return
            await self.send_command_help(context, p_cmd)
            return
        s_cmd = self.app.get_slash_command(obj)
        if s_cmd is not None and not s_cmd.hidden:
            if isinstance(s_cmd, (commands.slash.SlashCommandGroup, commands.slash.SlashSubGroup)):
                await self.send_group_help(context, s_cmd)
                return
            await self.send_command_help(context, s_cmd)
            return
        m_cmd = self.app.get_message_command(obj)
        if m_cmd is not None and not m_cmd.hidden:
            await self.send_command_help(context, m_cmd)
            return
        u_cmd = self.app.get_user_command(obj)
        if u_cmd is not None and not u_cmd.hidden:
            await self.send_command_help(context, u_cmd)
            return

        plugin = self.app.get_plugin(obj)
        if plugin is not None:
            await self.send_plugin_help(context, plugin)
            return

        await self.object_not_found(context, obj)

    @abc.abstractmethod
    async def send_bot_help(self, context: context_.base.Context) -> None:
        """
        Sends an overall help message for the bot. This is called when no object is provided
        when the help command is invoked.

        Args:
            context (:obj:`~.context.base.Context`): Context to send help to.

        Returns:
            ``None``
        """
        ...

    @abc.abstractmethod
    async def send_command_help(self, context: context_.base.Context, command: commands.base.Command) -> None:
        """
        Sends a help message for the given command.

        Args:
            context (:obj:`~.context.base.Context`): Context to send help to.
            command (:obj:`~.commands.base.Command`): Command to send help for.

        Returns:
            ``None``
        """
        ...

    @abc.abstractmethod
    async def send_group_help(
        self,
        context: context_.base.Context,
        group: t.Union[
            commands.prefix.PrefixCommandGroup,
            commands.prefix.PrefixSubGroup,
            commands.slash.SlashCommandGroup,
            commands.slash.SlashSubGroup,
        ],
    ) -> None:
        """
        Sends a help message for the given command group.

        Args:
            context (:obj:`~.context.base.Context`): Context to send help to.
            group: Command group to send help for.

        Returns:
            ``None``
        """
        ...

    @abc.abstractmethod
    async def send_plugin_help(self, context: context_.base.Context, plugin: plugins.Plugin) -> None:
        """
        Sends a help message for the given plugin.

        Args:
            context (:obj:`~.context.base.Context`): Context to send help to.
            plugin (:obj:`~.plugins.Plugin`): Plugin to send help for.

        Returns:
            ``None``
        """
        ...

    async def object_not_found(self, context: context_.base.Context, obj: str) -> None:
        """
        Method called when no object could be resolved from the given name.

        Args:
            context (:obj:`~.context.base.Context`): Context to send help to.
            obj (:obj:`str`): String that the help command was invoked with but that could not be resolved
                into an object.

        Returns:
            ``None``
        """
        await context.respond(f"No command or category with the name `{obj}` could be found.")


class DefaultHelpCommand(BaseHelpCommand):
    """
    An implementation of the :obj:`~BaseHelpCommand` that the bot uses by default.
    """

    @staticmethod
    async def _get_command_plugin_map(
        cmd_map: t.Mapping[str, commands.base.Command], context: context_.base.Context
    ) -> t.Dict[t.Optional[plugins.Plugin], t.List[commands.base.Command]]:
        out = collections.defaultdict(list)
        for cmd in cmd_map.values():
            if await filter_commands([cmd], context):
                out[cmd.plugin].append(cmd)
        return out

    @staticmethod
    def _add_cmds_to_plugin_pages(
        pages: t.MutableMapping[t.Optional[plugins.Plugin], t.List[str]],
        cmds: t.Mapping[t.Optional[plugins.Plugin], t.List[commands.base.Command]],
        header: str,
    ) -> None:
        for plugin, cmds in cmds.items():
            pages[plugin].append(f"== {header} Commands")
            for cmd in set(cmds):
                pages[plugin].append(f"- {cmd.name} - {cmd.description}")

    async def send_bot_help(self, context: context_.base.Context) -> None:
        pages = []
        lines = [
            ">>> ```adoc",
            "==== Bot Help ====",
            "",
            f"For more information: {context.prefix}help [command|category]",
            "",
            "==== Categories ====",
        ]
        for plugin in self.app._plugins.values():
            lines.append(f"- {plugin.name}")
        lines.append("```")

        pages.append("\n".join(lines))
        lines.clear()

        p_commands = await self._get_command_plugin_map(self.app._prefix_commands, context)
        s_commands = await self._get_command_plugin_map(self.app._slash_commands, context)
        m_commands = await self._get_command_plugin_map(self.app._message_commands, context)
        u_commands = await self._get_command_plugin_map(self.app._user_commands, context)

        plugin_pages: t.MutableMapping[t.Optional[plugins.Plugin], t.List[str]] = collections.defaultdict(list)
        self._add_cmds_to_plugin_pages(plugin_pages, p_commands, "Prefix")
        self._add_cmds_to_plugin_pages(plugin_pages, s_commands, "Slash")
        self._add_cmds_to_plugin_pages(plugin_pages, m_commands, "Message")
        self._add_cmds_to_plugin_pages(plugin_pages, u_commands, "User")

        for plugin, page in plugin_pages.items():
            pages.append(
                "\n".join(
                    [
                        ">>> ```adoc",
                        f"==== {plugin.name if plugin is not None else 'Uncategorised'} ====",
                        (f"{plugin.description}\n" if plugin.description else "No description provided\n")
                        if plugin is not None
                        else "",
                        *page,
                        "```",
                    ]
                )
            )

        navigator = nav.ButtonNavigator(pages)
        await navigator.run(context)

    async def send_command_help(self, context: context_.base.Context, command: commands.base.Command) -> None:
        long_help = command.get_help(context)
        prefix = (
            context.prefix
            if isinstance(command, commands.prefix.PrefixCommand)
            else "/"
            if isinstance(command, commands.slash.SlashCommand)
            else "\N{THREE BUTTON MOUSE}"
        )

        lines = [
            ">>> ```adoc",
            "==== Command Help ====",
            f"{command.name} - {command.description}",
            "",
            f"Usage: {prefix}{command.signature}",
            "",
            long_help if long_help else "No additional details provided.",
            "```",
        ]
        await context.respond("\n".join(lines))

    async def send_group_help(
        self,
        context: context_.base.Context,
        group: t.Union[
            commands.prefix.PrefixCommandGroup,
            commands.prefix.PrefixSubGroup,
            commands.slash.SlashCommandGroup,
            commands.slash.SlashSubGroup,
        ],
    ) -> None:
        long_help = group.get_help(context)
        prefix = (
            context.prefix
            if isinstance(group, commands.prefix.PrefixCommand)
            else "/"
            if isinstance(group, commands.slash.SlashCommand)
            else "\N{THREE BUTTON MOUSE}"
        )

        usages = list(
            filter(
                None,
                [
                    f"{prefix}{group.signature}" if isinstance(group, commands.prefix.PrefixCommand) else None,
                    f"{prefix}{group.qualname} [subcommand]",
                ],
            )
        )
        usages[0] = f"Usage: {usages[0]}"
        if len(usages) > 1:
            usages[1] = f"Or: {usages[1]}"

        lines = [
            ">>> ```adoc",
            "==== Group Help ====",
            f"{group.name} - {group.description}",
            "",
            "\n".join(usages),
            "",
            long_help if long_help else "No additional details provided.",
            "",
        ]
        if group._subcommands:
            subcommands = await filter_commands(group._subcommands.values(), context)  # type: ignore
            lines.append("== Subcommands")
            for cmd in set(subcommands):
                lines.append(f"- {cmd.name} - {cmd.description}")
        lines.append("```")
        await context.respond("\n".join(lines))

    async def send_plugin_help(self, context: context_.base.Context, plugin: plugins.Plugin) -> None:
        lines = [
            ">>> ```adoc",
            "==== Category Help ====",
            f"{plugin.name} - {plugin.description or 'No description provided'}",
            "",
        ]
        p_cmds, s_cmds, m_cmds, u_cmds = [], [], [], []
        all_commands = await filter_commands(plugin._all_commands, context)
        for cmd in all_commands:
            if isinstance(cmd, commands.prefix.PrefixCommand):
                p_cmds.append(cmd)
            elif isinstance(cmd, commands.slash.SlashCommand):
                s_cmds.append(cmd)
            elif isinstance(cmd, commands.message.MessageCommand):
                m_cmds.append(cmd)
            elif isinstance(cmd, commands.user.UserCommand):
                u_cmds.append(cmd)

        cmds: t.List[t.Tuple[t.Sequence[commands.base.Command], str]] = [
            (p_cmds, "Prefix"),
            (s_cmds, "Slash"),
            (m_cmds, "Message"),
            (u_cmds, "User"),
        ]
        for cmd_list, header in cmds:
            if cmd_list:
                lines.append(f"== {header} Commands")
                for cmd in set(cmd_list):
                    lines.append(f"- {cmd.name} - {cmd.description}")
        lines.append("```")
        await context.respond("\n".join(lines))
