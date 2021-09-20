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
    "Option",
    "BaseSlashCommand",
    "WithAsyncCallback",
    "WithGetCommand",
    "WithCreationMethods",
    "WithGetOptions",
    "WithAsOption",
    "SlashCommand",
    "SlashCommandGroup",
    "SlashSubGroup",
    "SlashSubCommand",
]

import abc
import collections.abc
import dataclasses
import functools
import inspect
import logging
import typing
import warnings

import hikari

from lightbulb import errors

if typing.TYPE_CHECKING:
    from lightbulb import checks as checks_
    from lightbulb import command_handler
    from lightbulb.slash_commands import context as context_

_LOGGER = logging.getLogger("lightbulb")

OPTION_TYPE_MAPPING = {
    str: hikari.OptionType.STRING,
    int: hikari.OptionType.INTEGER,
    bool: hikari.OptionType.BOOLEAN,
    hikari.User: hikari.OptionType.USER,
    hikari.TextableChannel: hikari.OptionType.CHANNEL,
    hikari.Role: hikari.OptionType.ROLE,
    hikari.Snowflake: hikari.OptionType.MENTIONABLE,
    float: hikari.OptionType.FLOAT,
}


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


def _serialise_command(cmd: typing.Union[hikari.Command, typing.Union[SlashCommand, SlashCommandGroup]]):
    opts = cmd.options if isinstance(cmd, hikari.Command) else cmd.get_options()
    return {
        "name": cmd.name.lower(),
        "description": cmd.description,
        "options": list(sorted((_serialise_option(opt) for opt in opts), key=lambda o: o["name"]))
        if opts is not None
        else [],
    }


def _resolve_subcommand(
    context: context_.SlashCommandContext,
    subcommands: typing.MutableMapping[str, typing.Union[SlashSubCommand, SlashSubGroup]],
) -> typing.Optional[str]:
    option_name = None
    for option in context.options:
        if option in subcommands:
            option_name = option
            break
    return option_name


@dataclasses.dataclass
class Option:
    """
    Dataclass representing a command option.

    Examples:
        Usage in a slash command:

        .. code-block:: python

            class Echo(SlashCommand):
                description = "Repeats the input"
                # Options
                text: str = Option("Text to repeat")

                async def callback(self, context):
                    await context.respond(context.option_values.text)

    """

    description: str
    """The description of the option."""
    name: typing.Optional[str] = None
    """The name of the option. If ``None`` then this will be the name of the attribute."""
    required: typing.Optional[bool] = None
    """Whether or not the option is required. If ``None`` then it will be inferred from the attribute's typehint."""
    choices: typing.Optional[typing.Sequence[str, int, float, hikari.Snowflakeish, hikari.CommandChoice]] = None
    """
    Sequence of the choices for the option. Defaults to None. 
    If :obj:`hikari.CommandChoice` objects are not provided then one will be built
    from the choice with the name set to the string representation of the value.
    """


def _get_type_and_required_from_option(hint, opt: Option) -> typing.Tuple[hikari.OptionType, bool]:
    type_ = OPTION_TYPE_MAPPING[typing.get_args(hint)[0] if typing.get_args(hint) else hint]
    required = opt.required if opt.required is not None else (type(None) not in typing.get_args(hint))
    return type_, required


def _get_choice_objects_from_choices(
    choices: typing.Sequence[str, int, float, hikari.Snowflakeish, hikari.CommandChoice]
):
    return [c if isinstance(c, hikari.CommandChoice) else hikari.CommandChoice(name=str(c), value=c) for c in choices]


def _get_options_for_command_instance(
    cmd: typing.Union[SlashCommand, SlashSubCommand]
) -> typing.Sequence[hikari.CommandOption]:
    if (
        hasattr(cmd, "options")
        and isinstance(cmd.options, collections.abc.Sequence)
        and not isinstance(cmd.options, str)
    ):
        warnings.warn(
            "Definition of command options in the 'options' attribute is deprecated and "
            "scheduled for removal in version 1.4. You should define options using class variables instead.",
            DeprecationWarning,
        )
        return cmd.options

    all_attrs = [[attr_name, getattr(cmd, attr_name)] for attr_name in dir(cmd)]
    opts = filter(lambda opt: type(opt[1]) is Option, all_attrs)
    hints = typing.get_type_hints(cmd if inspect.isclass(cmd) else type(cmd))

    hk_options = []
    for attr_name, option in opts:
        type_, required = _get_type_and_required_from_option(hints.get(attr_name), option)
        hk_options.append(
            hikari.CommandOption(
                name=option.name or attr_name,
                description=option.description,
                type=type_,
                is_required=required,
                **({"choices": _get_choice_objects_from_choices(option.choices)} if option.choices is not None else {}),
            )
        )
    return hk_options


class BaseSlashCommand(abc.ABC):
    """
    Abstract base class for slash command-like classes.

    Args:
        bot (:obj:`~lightbulb.command_handler.Bot`): The bot instance the command will be added to.
    """

    __slots__ = ("bot", "_instances")

    def __init__(self, bot: command_handler.Bot) -> None:
        self.bot = bot
        """The bot instance that the slash command is registered to."""
        self._instances: typing.MutableMapping[hikari.Snowflakeish, hikari.Command] = {}

    @property
    def name(self) -> str:
        """
        The name of the slash command. Defaults to the class name converted to lowercase. Can be a maximum
        of 32 characters long.

        Returns:
            :obj:`str`: Slash command name.
        """
        return self.__class__.__name__.lower()

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """
        The description of the slash command. Can be a maximum of 100 characters long.

        Returns:
            :obj:`str`: Slash command description.
        """
        ...


class WithAsyncCallback(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def callback(self, context: context_.SlashCommandContext) -> None:
        """
        The slash command callback method. This method will be called whenever the slash command is invoked.

        If the slash command being invoked is a subcommand then the
        :obj:`~lightbulb.slash_commands.SlashCommandContext.options`  attribute will have been replaced by the options
        that the subcommand was invoked with, instead of those that the command as a whole was invoked with  (they can
        still be accessed through :obj:`~lightbulb.slash_commands.SlashCommandContext.interaction.options` if necessary).

        Args:
            context (:obj:`~lightbulb.slash_commands.SlashCommandContext`): The context that the slash command
                was invoked under.

        Returns:
            ``None``
        """
        ...


class WithChecks(abc.ABC):
    async def evaluate_checks(self, context: context_.SlashCommandContext) -> bool:
        failed_checks = []
        for check in self.checks:
            try:
                result = await check(context)
                if not result:
                    failed_checks.append(errors.CheckFailure(f"Check {check.__name__} failed for command {self.name}"))
            except Exception as ex:
                error = errors.CheckFailure(str(ex))
                error.__cause__ = ex
                failed_checks.append(ex)

        if len(failed_checks) > 1:
            raise errors.CheckFailure("Multiple checks failed: " + ", ".join(str(ex) for ex in failed_checks))
        elif failed_checks:
            raise failed_checks[0]

        return True

    @property
    def checks(self) -> typing.Sequence[checks_.Check]:
        """
        The slash command's checks. These will be run in order before the slash command
        is invoked.

        Returns:
            Sequence[:obj:`~lightbulb.checks.Check`]: Checks to run before command invocation.
        """
        return []


class WithAsOption(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def as_option(self) -> hikari.CommandOption:
        """
        Creates and returns the appropriate :obj:`hikari.CommandOption` representation for this
        subcommand class.

        Returns:
            :obj:`hikari.CommandOption`: The ``CommandOption`` version of the subcommand class.
        """
        ...


class WithGetOptions(abc.ABC):
    __slots__ = ()

    @property
    def enabled_guilds(self) -> typing.Optional[typing.Union[hikari.Snowflakeish, hikari.SnowflakeishSequence]]:
        """
        The guilds that the slash command is enabled in. If ``None`` or an empty sequence, the command will be
        added as a global command. Defaults to an empty list, therefore making the command global unless otherwise
        specified.

        Returns:
            Optional[Union[:obj:`hikari.Snowflakeish`, :obj:`hikari.SnowflakeishSequence`]]: Guilds that the command
                is enabled in, or ``None`` or empty sequence if the command is global.
        """
        return []

    @abc.abstractmethod
    def get_options(self) -> typing.Sequence[hikari.CommandOption]:
        """
        Get the options for the command.

        Returns:
            Sequence[:obj:`hikari.CommandOption`]: Options for the command.
        """
        ...


class WithCreationMethods(abc.ABC):
    __slots__ = ()

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
        if not self.enabled_guilds:
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
        if not self.enabled_guilds:
            await self.delete(app)
        else:
            for guild_id in self.enabled_guilds:
                await self.delete(app, guild_id)


class WithGetCommand(abc.ABC):
    __slots__ = ()

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


class SlashCommand(
    BaseSlashCommand, WithGetOptions, WithAsyncCallback, WithCreationMethods, WithGetCommand, WithChecks, abc.ABC
):
    """
    Abstract base class for top level slash commands. All slash commands that are not groups
    should inherit from this class.

    All abstract methods **must** be implemented by your custom slash command class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.BaseSlashCommand.description` (class variable)
    - :obj:`~lightbulb.slash_commands.WithAsyncCallback.callback` (instance method)
    """

    __slots__ = ()

    async def __call__(self, *args, **kwargs):
        await self.evaluate_checks(*args, **kwargs)
        return await self.callback(*args, **kwargs)

    @functools.lru_cache
    def get_options(self) -> typing.Sequence[hikari.CommandOption]:
        hk_options = _get_options_for_command_instance(self)
        return list(sorted(hk_options, key=lambda o: o.is_required, reverse=True))

    async def create(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> hikari.Command:
        created_command = await self.bot.rest.create_application_command(
            app,
            self.name,
            self.description,
            options=self.get_options(),
            **({"guild": guild_id} if guild_id is not None else {}),
        )
        self._instances[guild_id] = created_command
        return created_command


class SlashCommandGroup(BaseSlashCommand, WithGetOptions, WithCreationMethods, WithGetCommand, abc.ABC):
    """
    Abstract base class for slash command groups. All slash command groups should inherit from this class.

    All abstract methods **must** be implemented by your custom slash command group class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.BaseSlashCommand.description` (class variable)
    """

    __slots__ = ("_subcommands",)

    _subcommand_dict: typing.Dict[
        str, typing.List[typing.Type[SlashSubCommand], typing.Type[SlashSubGroup]]
    ] = collections.defaultdict(list)

    def __init__(self, bot: command_handler.Bot):
        super().__init__(bot)
        self._subcommands: typing.MutableMapping[str, SlashSubCommand] = {}
        for cmd_class in self._subcommand_dict.get(self.__class__.__name__.lower(), []):
            cmd = cmd_class(bot)
            self._subcommands[cmd.name] = cmd

    @functools.lru_cache
    def get_options(self) -> typing.Sequence[hikari.CommandOption]:
        return [cmd.as_option() for cmd in self._subcommands.values()]

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
            cls._subcommand_dict[cls.__name__.lower()].append(subcommand_class)
            return subcommand_class

        return decorate

    @classmethod
    def subgroup(cls) -> typing.Callable[[typing.Type[SlashSubGroup]], typing.Type[SlashSubGroup]]:
        """
        Decorator which registers a subgroup to this slash command group.
        """

        def decorate(subgroup_class: typing.Type[SlashSubGroup]) -> typing.Type[SlashSubGroup]:
            cls._subcommand_dict[cls.__name__.lower()].append(subgroup_class)
            return subgroup_class

        return decorate

    async def create(
        self,
        app: hikari.SnowflakeishOr[hikari.PartialApplication],
        guild_id: typing.Optional[hikari.Snowflakeish] = None,
    ) -> hikari.Command:
        created_command = await self.bot.rest.create_application_command(
            app,
            self.name,
            self.description,
            options=self.get_options(),
            **({"guild": guild_id} if guild_id is not None else {}),
        )
        self._instances[guild_id] = created_command
        return created_command


class SlashSubGroup(BaseSlashCommand, WithAsOption, abc.ABC):
    """
    Abstract base class for slash subgroups. All slash subgroups should inherit from this class.

    All abstract methods **must** be implemented by your custom slash subgroup class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.BaseSlashCommand.description` (class variable)
    """

    __slots__ = ("_subcommands",)

    _subcommand_dict: typing.Dict[str, typing.List[typing.Type[SlashSubCommand]]] = collections.defaultdict(list)

    def __init__(self, bot: command_handler.Bot):
        super().__init__(bot)
        self._subcommands: typing.MutableMapping[str, SlashSubCommand] = {}
        for cmd_class in self._subcommand_dict.get(self.__class__.__name__.lower(), []):
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
            cls._subcommand_dict[cls.__name__.lower()].append(subcommand_class)
            return subcommand_class

        return decorate

    @functools.lru_cache
    def as_option(self) -> hikari.CommandOption:
        return hikari.CommandOption(
            name=self.name,
            description=self.description,
            type=hikari.OptionType.SUB_COMMAND_GROUP,
            options=[cmd.as_option() for cmd in self._subcommands.values()],
            is_required=False,
        )


class SlashSubCommand(BaseSlashCommand, WithAsOption, WithAsyncCallback, WithChecks, abc.ABC):
    """
    Abstract base class for slash subcommands. All slash subcommands should inherit from this class.

    All abstract methods **must** be implemented by your custom slash subcommand class. A list of the abstract
    methods and properties you are required to implement for this class can be seen below:

    - :obj:`~lightbulb.slash_commands.BaseSlashCommand.description` (class variable)
    - :obj:`~lightbulb.slash_commands.WithAsyncCallback.callback` (instance method)
    """

    __slots__ = ()

    async def __call__(self, *args, **kwargs):
        await self.evaluate_checks(*args, **kwargs)
        return await self.callback(*args, **kwargs)

    @functools.lru_cache
    def as_option(self) -> hikari.CommandOption:
        hk_options = _get_options_for_command_instance(self)
        return hikari.CommandOption(
            name=self.name,
            description=self.description,
            type=hikari.OptionType.SUB_COMMAND,
            options=list(sorted(hk_options, key=lambda o: o.is_required, reverse=True)),
            is_required=False,
        )
