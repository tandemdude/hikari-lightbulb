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

__all__ = ["BaseHelpCommand"]

import abc
import typing as t

from lightbulb import commands

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb import context as context_
    from lightbulb import plugins


class BaseHelpCommand(abc.ABC):
    def __init__(self, app: app_.BotApp) -> None:
        self.app = app

    async def send_help(self, context: context_.base.Context, obj: str) -> None:
        await self._send_help(context, obj)

    async def _send_help(self, context: context_.base.Context, obj: str) -> None:
        p_cmd = self.app.get_prefix_command(obj)
        if p_cmd is not None:
            if isinstance(p_cmd, (commands.prefix.PrefixCommandGroup, commands.prefix.PrefixSubGroup)):
                await self.send_group_help(context, p_cmd)
                return
            await self.send_command_help(context, p_cmd)
            return
        s_cmd = self.app.get_slash_command(obj)
        if s_cmd is not None:
            if isinstance(s_cmd, (commands.slash.SlashCommandGroup, commands.slash.SlashSubGroup)):
                await self.send_group_help(context, s_cmd)
                return
            await self.send_command_help(context, s_cmd)
            return
        m_cmd = self.app.get_message_command(obj)
        if m_cmd is not None:
            await self.send_command_help(context, m_cmd)
            return
        u_cmd = self.app.get_user_command(obj)
        if u_cmd is not None:
            await self.send_command_help(context, u_cmd)
            return

        plugin = self.app.get_plugin(obj)
        if plugin is not None:
            await self.send_plugin_help(context, plugin)
            return

        await self.object_not_found(context)

    @abc.abstractmethod
    async def send_bot_help(self, context: context_.base.Context) -> None:
        ...

    @abc.abstractmethod
    async def send_command_help(self, context: context_.base.Context, command: commands.base.Command) -> None:
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
        ...

    @abc.abstractmethod
    async def send_plugin_help(self, context: context_.base.Context, plugin: plugins.Plugin) -> None:
        ...

    @abc.abstractmethod
    async def object_not_found(self, context: context_.base.Context) -> None:
        ...
