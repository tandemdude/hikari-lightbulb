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

__all__: typing.Final[typing.List[str]] = [
    "SlashCommandBase",
    "TopLevelSlashCommandBase",
    "SlashCommand",
    "SlashCommandGroup",
    "SlashSubGroup",
    "SlashSubCommand",
]

import abc
import logging
import typing

import hikari

if typing.TYPE_CHECKING:
    from lightbulb import command_handler
    from lightbulb.slash_commands import context as context_

_LOGGER = logging.getLogger("lightbulb")


def _serialise_option(opt: hikari.CommandOption):
    data = {
        "name": opt.name.lower(),
        "description": opt.description,
        "type": opt.type,
        "required": opt.is_required,
    }

    if opt.options is not None:
        data["options"] = list(
            sorted((_serialise_option(sub_option) for sub_option in opt.options), key=lambda o: o["name"])
        )
    elif opt.choices is not None:
        data["choices"] = list(
            sorted(({"name": c.name.lower(), "value": c.value} for c in opt.choices), key=lambda c: c["name"])
        )
    else:
        data["options"] = []

    return data


def _serialise_command(cmd: typing.Union[hikari.Command, TopLevelSlashCommandBase]):
    return {
        "name": cmd.name.lower(),
        "description": cmd.description,
        "options": list(sorted((_serialise_option(opt) for opt in cmd.options), key=lambda o: o["name"]))
        if cmd.options is not None
        else [],
    }


def _resolve_subcommand(
    context: context_.SlashCommandContext, subcommands: typing.MutableMapping[str, SlashCommandBase]
) -> typing.Optional[str]:
    option_name = None
    for option in context.options:
        if option in subcommands:
            option_name = option
            break
    return option_name


class SlashCommandBase(abc.ABC):
    """
    Abstract base class for slash command-like classes.

    Args:
        bot (:obj:`~lightbulb.command_handler.Bot`): The bot instance the command will be added to.
    """

    __slots__: typing.Sequence[str] = ("bot", "_instances")

    def __init__(self, bot: command_handler.Bot) -> None:
        self.bot = bot
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


class TopLevelSlashCommandBase(SlashCommandBase, abc.ABC):
    """
    Abstract base class for top level slash commands and slash command groups.
    """

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
    ) -> hikari.Command:
        """
        Creates the command for a specific guild, or globally if no guild ID is given.

        Args:
            app (hikari.SnowflakeishOr[hikari.PartialApplication]): The application to add the command to.
            guild_id (Optional[:obj:`int`]): The ID of the guild to create the command for.

        Returns:
            :obj:`hikari.Command`: The command object created.
        """
        ...

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
        await self.bot.rest.delete_application_command(
            app, self._instances[guild_id], **({"guild": guild_id} if guild_id is not None else {})
        )
        self._instances.pop(guild_id)

    async def auto_create(self, app: hikari.SnowflakeishOr[hikari.PartialApplication]) -> None:
        """
        Creates the command in the appropriate scopes (guilds, global) automatically.

        Args:
            app (hikari.SnowflakeishOr[hikari.PartialApplication]): The application to add the command to.

        Returns:
            ``None``
        """
        if self.enabled_guilds is None:
            await self.create(app)
        else:
            for guild_id in self.enabled_guilds:
                await self.create(app, guild_id)

    async def auto_delete(self, app: hikari.SnowflakeishOr[hikari.PartialApplication]) -> None:
        """
        Deletes the command from the appropriate scopes (guilds, global) automatically.

        Args:
            app (hikari.SnowflakeishOr[hikari.PartialApplication]): The application to remove the command from.

        Returns:
            ``None``
        """
        if self.enabled_guilds is None:
            await self.delete(app)
        else:
            for guild_id in self.enabled_guilds:
                await self.delete(app, guild_id)

    def get_command(self, guild_id: typing.Optional[hikari.Snowflakeish] = None) -> typing.Optional[hikari.Command]:
        """
        Gets the :obj:`hikari.Command` instance of this command class for a given ``guild_id``, or the global
        instance if no ``guild_id`` is provided. Returns ``None`` if no instance is found for the given ``guild_id``.

        Args:
            guild_id (Optional[:obj:`hikari.Snowflakeish`): The guild ID to get the :obj:`hikari.Command` instance
                for.

        Returns:
            Optional[:obj:`hikari.Command`]: Command instance for that guild, or ``None`` if no instance exists.
        """
        return self._instances.get(guild_id)


class SlashCommand(TopLevelSlashCommandBase, abc.ABC):
    """
    Abstract base class for top level slash commands. All slash commands that are not groups
    should inherit from this class.

    All abstract methods **must** be implemented by your custom slash command class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.SlashCommandBase.description` (class variable/property)
    - :obj:`~lightbulb.slash_commands.SlashCommand.options` (class variable/property)
    - :obj:`~lightbulb.slash_commands.TopLevelSlashCommandBase.enabled_guilds` (class variable/property)
    - :obj:`~lightbulb.slash_commands.SlashCommand.callback` (instance method)
    """

    __slots__: typing.Sequence[str] = ()

    async def __call__(self, context: context_.SlashCommandContext) -> None:
        return await self.callback(context)

    async def create(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> hikari.Command:
        created_command = await self.bot.rest.create_application_command(
            app,
            self.name,
            self.description,
            options=self.options,
            **({"guild": guild_id} if guild_id is not None else {}),
        )
        self._instances[guild_id] = created_command
        return created_command

    @property
    @abc.abstractmethod
    def options(self) -> typing.Sequence[hikari.CommandOption]:
        """
        The slash command options. Can include up to a maximum of 25 options.
        """
        ...

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


class SlashSubCommand(SlashCommandBase, abc.ABC):
    """
    Abstract base class for slash subcommands. All slash subcommands should inherit from this class.

    All abstract methods **must** be implemented by your custom slash subcommand class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.SlashCOmmandBase.description` (class variable/property)
    - :obj:`~lightbulb.slash_commands.SlashSubCommand.options` (class variable/property)
    - :obj:`~lightbulb.slash_commands.SlashSubCommand.callback` (instance method)
    """

    async def __call__(self, context: context_.SlashCommandContext) -> None:
        return await self.callback(context)

    def as_option(self) -> hikari.CommandOption:
        """
        Creates and returns the appropriate :obj:`hikari.CommandOption` representation for this
        subcommand class.

        Returns:
            :obj:`hikari.CommandOption`: The ``CommandOption`` version of the subcommand class.
        """
        return hikari.CommandOption(
            name=self.name,
            description=self.description,
            type=hikari.OptionType.SUB_COMMAND,
            options=self.options,
            is_required=False,
        )

    @abc.abstractmethod
    async def callback(self, context: context_.SlashCommandContext) -> None:
        """
        The subcommand callback method. This method will be called whenever the  subcommand is invoked.

        Args:
            context (:obj:`~lightbulb.slash_commands.SlashCommandContext`): The context that the subcommand
                was invoked under. The :obj:`~lightbulb.slash_commands.SlashCommandContext.options` attribute
                will have been replaced by the options that the subcommand was invoked with, instead of those that
                the command as a whole was invoked with  (they can still be accessed through
                :obj:`~lightbulb.slash_commands.SlashCommandContext.interaction.options` if necessary).

        Returns:
            ``None``
        """
        ...

    @property
    @abc.abstractmethod
    def options(self) -> typing.Sequence[hikari.CommandOption]:
        """
        The subcommand options. Can include up to a maximum of 25 options.
        """
        ...


class SlashSubGroup(SlashCommandBase, abc.ABC):
    """
    Abstract base class for slash subgroups. All slash subgroups should inherit from this class.

    All abstract methods **must** be implemented by your custom slash subgroup class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.SlashCommandBase.description` (class variable/property)
    """

    __slots__: typing.Sequence[str] = ("_subcommands",)

    _subcommand_list: typing.List[typing.Type[SlashSubCommand]] = []

    def __init__(self, bot: command_handler.Bot):
        super().__init__(bot)
        self._subcommands: typing.MutableMapping[str, SlashSubCommand] = {}
        for cmd_class in self._subcommand_list:
            cmd = cmd_class(bot)
            self._subcommands[cmd.name] = cmd

    async def __call__(self, context: context_.SlashCommandContext) -> None:
        option_name = _resolve_subcommand(context, self._subcommands)
        if option_name is None:
            return

        _LOGGER.debug("invoking slash subcommand %r", option_name)
        # Replace the context options with the options for the subcommand, the old options
        # can still be accessed through context.interaction.options
        new_options = context.options[option_name].options
        context.options = {option.name: option for option in new_options} if new_options is not None else {}
        return await self._subcommands[option_name](context)

    @classmethod
    def subcommand(cls) -> typing.Callable[[typing.Type[SlashSubCommand]], typing.Type[SlashSubCommand]]:
        """
        Decorator which registers a subcommand to this slash command group.
        """

        def decorate(subcommand_class: typing.Type[SlashSubCommand]) -> typing.Type[SlashSubCommand]:
            cls._subcommand_list.append(subcommand_class)
            return subcommand_class

        return decorate

    def as_option(self) -> hikari.CommandOption:
        """
        Creates and returns the appropriate :obj:`hikari.CommandOption` representation for this
        subgroup class.

        Returns:
            :obj:`hikari.CommandOption`: The ``CommandOption`` version of the subgroup class.
        """
        return hikari.CommandOption(
            name=self.name,
            description=self.description,
            type=hikari.OptionType.SUB_COMMAND_GROUP,
            options=[cmd.as_option() for cmd in self._subcommands.values()],
            is_required=False,
        )


class SlashCommandGroup(TopLevelSlashCommandBase, abc.ABC):
    """
    Abstract base class for slash command groups. All slash command groups should inherit from this class.

    All abstract methods **must** be implemented by your custom slash command group class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.SlashCommandBase.description` (class variable/property)
    - :obj:`~lightbulb.slash_commands.TopLevelSlashCommandBase.enabled_guilds` (class variable/property)
    """

    __slots__: typing.Sequence[str] = ("_subcommands",)

    _subcommand_list: typing.List[typing.Union[typing.Type[SlashSubCommand], typing.Type[SlashSubGroup]]] = []

    def __init__(self, bot: command_handler.Bot):
        super().__init__(bot)
        self._subcommands: typing.MutableMapping[str, SlashSubCommand] = {}
        for cmd_class in self._subcommand_list:
            cmd = cmd_class(bot)
            self._subcommands[cmd.name] = cmd

    async def __call__(self, context: context_.SlashCommandContext) -> None:
        option_name = _resolve_subcommand(context, self._subcommands)
        if option_name is None:
            return

        _LOGGER.debug("invoking slash subcommand %r", option_name)
        # Replace the context options with the options for the subcommand, the old options
        # can still be accessed through context.interaction.options
        new_options = context.options[option_name].options
        context.options = {option.name: option for option in new_options} if new_options is not None else {}
        return await self._subcommands[option_name](context)

    @classmethod
    def subcommand(cls) -> typing.Callable[[typing.Type[SlashSubCommand]], typing.Type[SlashSubCommand]]:
        """
        Decorator which registers a subcommand to this slash command group.
        """

        def decorate(subcommand_class: typing.Type[SlashSubCommand]) -> typing.Type[SlashSubCommand]:
            cls._subcommand_list.append(subcommand_class)
            return subcommand_class

        return decorate

    @classmethod
    def subgroup(cls) -> typing.Callable[[typing.Type[SlashSubGroup]], typing.Type[SlashSubGroup]]:
        """
        Decorator which registers a subgroup to this slash command group.
        """

        def decorate(subgroup_class: typing.Type[SlashSubGroup]) -> typing.Type[SlashSubGroup]:
            cls._subcommand_list.append(subgroup_class)
            return subgroup_class

        return decorate

    @property
    def options(self) -> typing.Sequence[hikari.CommandOption]:
        """
        A list of the group's subcommands as hikari ``CommandOption`` objects.
        """
        return [cmd.as_option() for cmd in self._subcommands.values()]

    async def create(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> hikari.Command:
        created_command = await self.bot.rest.create_application_command(
            app,
            self.name,
            self.description,
            options=[cmd.as_option() for cmd in self._subcommands.values()],
            **({"guild": guild_id} if guild_id is not None else {}),
        )
        self._instances[guild_id] = created_command
        return created_command
