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
from __future__ import annotations

__all__: typing.Final[typing.List[str]] = ["SlashCommandBase", "SlashCommand"]

import abc
import typing

import hikari

if typing.TYPE_CHECKING:
    from lightbulb import command_handler
    from lightbulb.slash_commands import context as context_


class SlashCommandBase(abc.ABC):
    """
    Abstract base class for slash commands and slash command groups.

    Args:
        bot (:obj:`~lightbulb.command_handler.Bot`): The bot instance the command will be added to.
    """

    def __init__(self, bot: command_handler.Bot):
        self._bot = bot
        self._instances: typing.MutableMapping[hikari.Snowflakeish, hikari.Command] = {}

    @abc.abstractmethod
    async def __call__(self, context: context_.SlashCommandContext) -> None:
        ...

    @property
    def name(self) -> str:
        """
        The name of the slash command. Defaults to the class name converted to lowercase. Can be a maximum
        of 32 characters long.
        """
        return self.__class__.__name__.lower()

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """
        The description of the slash command. Can be a maximum of 100 characters long.
        """
        ...

    @property
    @abc.abstractmethod
    def options(self) -> typing.Sequence[hikari.CommandOption]:
        """
        The slash command options. Can include a maximum of 25 options.
        """
        ...

    @property
    @abc.abstractmethod
    def enabled_guilds(self) -> typing.Optional[hikari.SnowflakeishSequence]:
        """
        The guilds that the slash command is enabled in. If ``None``, the command will be added as
        a global command.
        """
        ...

    @abc.abstractmethod
    async def create(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> None:
        """
        Creates the command for a specific guild, or globally if no guild ID is given.
        Args:
            app (hikari.SnowflakeishOr[hikari.PartialApplication]): The application to add the command to.
            guild_id (Optional[:obj:`int`]): The ID of the guild to create the command for.
        Returns:
            :obj:`hikari.Command`: The command object created.
        """
        ...

    @abc.abstractmethod
    async def delete(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> None:
        """
        Deletes the command for a specific guild, or globally if no guild ID is given.
        Args:
            app (hikari.SnowflakeishOr[hikari.PartialApplication]): The application to delete the command from.
            guild_id (Optional[hikari.Snowflakeish]): The ID of the guild to delete the command for.
        Returns:
            ``None``
        """
        ...

    async def auto_create(self, app: hikari.SnowflakeishOr[hikari.PartialApplication]) -> None:
        """
        Creates the command in the required scopes (guilds, global) automatically.

        Args:
            app (hikari.SnowflakeishOr[hikari.PartialApplication]): The application to add the command to.

        Returns:
            ``None``
        """
        if self.enabled_guilds is None:
            await self.create(app)
            return
        for guild_id in self.enabled_guilds:
            await self.create(app, guild_id)


class SlashCommand(SlashCommandBase, abc.ABC):
    """
    Abstract base class for top level slash commands. All slash commands that are not groups
    should inherit from this class.

    All abstract methods **must** be implemented by your custom slash command class.
    """

    async def __call__(self, context: context_.SlashCommandContext) -> None:
        return await self.callback(context)

    async def create(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> None:
        created_command = await self._bot.rest.create_application_command(
            app,
            self.name,
            self.description,
            options=self.options,
            **({"guild": guild_id} if guild_id is not None else {}),
        )
        self._instances[guild_id] = created_command
        return created_command

    async def delete(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> None:
        await self._bot.rest.delete_application_command(
            app, self._instances[guild_id], **({"guild": guild_id} if guild_id is not None else {})
        )
        self._instances.pop(guild_id)

    @abc.abstractmethod
    async def callback(self, context: context_.SlashCommandContext) -> None:
        """
        The slash command callback method. This method will be called whenever the slash command is invoked.

        Args:
            context (:obj:`~lightbulb.slash_commands.SlashCommandContext`): The context that the slash command
                was invoked under.

        Returns:
            ``None``
        """
        ...
