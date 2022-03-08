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

__all__ = ["OptionModifier", "OptionLike", "CommandLike", "Command", "ApplicationCommand", "SubCommandTrait"]

import abc
import asyncio
import collections
import dataclasses
import datetime
import enum
import inspect
import re
import typing as t

import hikari

from lightbulb import errors

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb import buckets
    from lightbulb import checks
    from lightbulb import context as context_
    from lightbulb import cooldowns
    from lightbulb import events
    from lightbulb import plugins
    from lightbulb.utils import parser as parser_

_AutocompleteableOptionT = t.Union[str, int, float]
AutocompleteCallbackT = t.TypeVar(
    "AutocompleteCallbackT",
    bound=t.Callable[
        ...,
        t.Coroutine[
            t.Any,
            t.Any,
            t.Union[
                _AutocompleteableOptionT,
                hikari.CommandChoice,
                t.Sequence[t.Union[_AutocompleteableOptionT, hikari.CommandChoice]],
            ],
        ],
    ],
)


class CommandCallbackT(t.Protocol):
    def __call__(self, context: context_.base.Context, **kwargs: t.Any) -> t.Coroutine[t.Any, t.Any, None]:
        ...


OPTION_TYPE_MAPPING = {
    str: hikari.OptionType.STRING,
    int: hikari.OptionType.INTEGER,
    float: hikari.OptionType.FLOAT,
    bool: hikari.OptionType.BOOLEAN,
    hikari.User: hikari.OptionType.USER,
    hikari.Member: hikari.OptionType.USER,
    hikari.GuildChannel: hikari.OptionType.CHANNEL,
    hikari.TextableGuildChannel: hikari.OptionType.CHANNEL,
    hikari.TextableChannel: hikari.OptionType.CHANNEL,
    hikari.GuildCategory: hikari.OptionType.CHANNEL,
    hikari.GuildVoiceChannel: hikari.OptionType.CHANNEL,
    hikari.Role: hikari.OptionType.ROLE,
    hikari.Emoji: hikari.OptionType.STRING,
    hikari.Guild: hikari.OptionType.STRING,
    hikari.Message: hikari.OptionType.STRING,
    hikari.Invite: hikari.OptionType.STRING,
    hikari.Colour: hikari.OptionType.STRING,
    hikari.Color: hikari.OptionType.STRING,
    hikari.Snowflake: hikari.OptionType.STRING,
    datetime.datetime: hikari.OptionType.STRING,
    hikari.Attachment: hikari.OptionType.ATTACHMENT,
}
OPTION_NAME_REGEX: re.Pattern[str] = re.compile(r"^[\w-]{1,32}$", re.U)


class _HasRecreateSubcommands(t.Protocol):
    app: app_.BotApp

    def recreate_subcommands(self, raw_cmds: t.Sequence[CommandLike], app: app_.BotApp) -> None:
        ...


class _SubcommandListProxy(collections.UserList):  # type: ignore
    __slots__ = ("parents",)

    def __init__(self, *args: t.Any, parent: _HasRecreateSubcommands, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.parents = [parent]

    def append(self, item: t.Any) -> None:
        super().append(item)
        for parent in self.parents:
            parent.recreate_subcommands(self.data, parent.app)

    def add_parent(self, parent: _HasRecreateSubcommands) -> _SubcommandListProxy:
        self.parents.append(parent)
        return self


def _get_choice_objects_from_choices(
    choices: t.Sequence[t.Union[str, int, float, hikari.CommandChoice]]
) -> t.Sequence[hikari.CommandChoice]:
    return [c if isinstance(c, hikari.CommandChoice) else hikari.CommandChoice(name=str(c), value=c) for c in choices]


class OptionModifier(enum.Enum):
    """Enum representing option modifiers that affect parsing for prefix commands."""

    NONE = enum.auto()
    """No modifier. This will be parsed as a normal argument."""
    GREEDY = enum.auto()
    """Greedy option. This will consume arguments until the string is exhausted or conversion fails."""
    CONSUME_REST = enum.auto()
    """Consume rest option. This will consume the entire remainder of the string."""


@dataclasses.dataclass
class OptionLike:
    """
    Generic dataclass representing a command option. Compatible with both prefix and application commands.
    """

    name: str
    """The name of the option."""
    description: str
    """The description of the option"""
    arg_type: t.Any = str
    """The type of the option."""
    required: bool = True
    """Whether or not the option is required. This will be inferred from whether or not a default value was provided if unspecified."""
    choices: t.Optional[t.Sequence[t.Union[str, int, float, hikari.CommandChoice]]] = None
    """The option's choices. This only affects slash commands."""
    channel_types: t.Optional[t.Sequence[hikari.ChannelType]] = None
    """The channel types for this option. This only affects slash commands."""
    default: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED
    """The default value for this option."""
    modifier: OptionModifier = OptionModifier.NONE
    """Additional modifier controlling how the option should be parsed. This only affects prefix commands."""
    min_value: t.Optional[t.Union[float, int]] = None
    """The minimum value permitted for this option (inclusive). The option must be ``INTEGER`` or ``FLOAT`` to use this."""
    max_value: t.Optional[t.Union[float, int]] = None
    """The maximum value permitted for this option (inclusive). The option must be ``INTEGER`` or ``FLOAT`` to use this."""
    autocomplete: bool = False
    """Whether the option should be autocompleted or not. This only affects slash commands."""

    def as_application_command_option(self) -> hikari.CommandOption:
        """
        Convert this object into a :obj:`~hikari.commands.CommandOption`.

        Returns:
            :obj:`~hikari.commands.CommandOption`: Created ``CommandOption`` object.
        """
        if not OPTION_NAME_REGEX.fullmatch(self.name) or self.name != self.name.lower():
            raise ValueError(
                f"Application command option {self.name!r}: name must match regex '^[\\w-]{1,32}$' and be all lowercase"
            )
        if len(self.description) < 1 or len(self.description) > 100:
            raise ValueError(
                f"Application command option {self.name!r}: description must be from 1-100 characters long"
            )

        arg_type = OPTION_TYPE_MAPPING.get(self.arg_type, self.arg_type)
        if not isinstance(arg_type, hikari.OptionType):
            arg_type = hikari.OptionType.STRING  # type: ignore[unreachable]

        if (self.min_value is not None or self.max_value is not None) and arg_type not in (
            hikari.OptionType.INTEGER,
            hikari.OptionType.FLOAT,
        ):
            raise ValueError(
                f"Application command option {self.name!r}: 'min_value' or 'max_value' was provided but the option type is not numeric"
            )

        if (
            arg_type not in (hikari.OptionType.INTEGER, hikari.OptionType.FLOAT, hikari.OptionType.STRING)
            and self.autocomplete
        ):
            raise ValueError(
                f"Application command option {self.name!r}: 'autocomplete' is True but the option type does not support choices"
            )

        kwargs: t.MutableMapping[str, t.Any] = {
            "type": arg_type,
            "name": self.name,
            "description": self.description,
            "is_required": self.required,
            "autocomplete": self.autocomplete,
        }

        if self.choices:
            if len(self.choices) > 25:
                raise ValueError("Application command options can have at most 25 choices")
            kwargs["choices"] = _get_choice_objects_from_choices(self.choices)

        if self.channel_types:
            kwargs["channel_types"] = self.channel_types

        if self.min_value is not None:
            kwargs["min_value"] = (
                int(self.min_value) if arg_type is hikari.OptionType.INTEGER else float(self.min_value)
            )

        if self.max_value is not None:
            kwargs["max_value"] = (
                int(self.max_value) if arg_type is hikari.OptionType.INTEGER else float(self.max_value)
            )

        return hikari.CommandOption(**kwargs)


@dataclasses.dataclass
class CommandLike:
    """Generic dataclass representing a command. This can be converted into any command object."""

    callback: CommandCallbackT
    """The callback function for the command."""
    name: str
    """The name of the command."""
    description: str
    """The description of the command."""
    options: t.MutableMapping[str, OptionLike] = dataclasses.field(default_factory=dict)
    """The options for the command."""
    checks: t.Sequence[t.Union[checks.Check, checks._ExclusiveCheck]] = dataclasses.field(default_factory=list)
    """The checks for the command."""
    error_handler: t.Optional[
        t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]
    ] = None
    """The error handler for the command."""
    aliases: t.Sequence[str] = dataclasses.field(default_factory=list)
    """The aliases for the command. This only affects prefix commands."""
    guilds: hikari.UndefinedOr[t.Sequence[int]] = hikari.UNDEFINED
    """The guilds for the command. This only affects application commands."""
    subcommands: t.List[CommandLike] = dataclasses.field(default_factory=list)
    """Subcommands for the command."""
    parser: t.Optional[t.Type[parser_.BaseParser]] = None
    """The argument parser to use for prefix commands."""
    cooldown_manager: t.Optional[cooldowns.CooldownManager] = None
    """The cooldown manager for the command."""
    help_getter: t.Optional[t.Callable[[Command, context_.base.Context], str]] = None
    """The function to call to get the command's long help text."""
    auto_defer: bool = False
    """Whether or not to automatically defer the response when the command is invoked."""
    ephemeral: bool = False
    """Whether or not to send responses from this command as ephemeral messages by default."""
    check_exempt: t.Optional[t.Callable[[context_.base.Context], t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]]] = None
    """Check exempt predicate to use for the command."""
    hidden: bool = False
    """Whether or not the command should be hidden from the help command."""
    inherit_checks: bool = False
    """Whether or not the command should inherit checks from the parent group."""
    pass_options: bool = False
    """Whether or not the command will have its options passed as keyword arguments when invoked."""
    max_concurrency: t.Optional[t.Tuple[int, t.Type[buckets.Bucket]]] = None
    """The max concurrency rule for the command."""
    _autocomplete_callbacks: t.Dict[
        str,
        t.Callable[
            [hikari.CommandInteractionOption, hikari.AutocompleteInteraction],
            t.Coroutine[
                t.Any,
                t.Any,
                t.Union[
                    _AutocompleteableOptionT,
                    hikari.CommandChoice,
                    t.Sequence[t.Union[_AutocompleteableOptionT, hikari.CommandChoice]],
                ],
            ],
        ],
    ] = dataclasses.field(default_factory=dict, init=False)

    async def __call__(self, context: context_.base.Context) -> None:
        await self.callback(context)

    def set_error_handler(
        self,
        func: t.Optional[t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]] = None,
    ) -> t.Union[
        t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]],
        t.Callable[
            [t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]],
            t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]],
        ],
    ]:
        """
        Registers a coroutine function as an error handler for this command. This can be used as a first or second
        order decorator, or called manually with the function to register.
        """
        if func is not None:
            self.error_handler = func
            return func

        def decorate(
            func_: t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]
        ) -> t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]:
            self.error_handler = func_
            return func_

        return decorate

    def child(
        self, cmd_like: t.Optional[CommandLike] = None
    ) -> t.Union[CommandLike, t.Callable[[CommandLike], CommandLike]]:
        """
        Registers a :obj:`~CommandLike` object as a child to this command. This can be used as a first or second
        order decorator, or called manually with the :obj:`~CommandLike` instance to add as a child.
        """
        if cmd_like is not None:
            self.subcommands.append(cmd_like)
            return cmd_like

        def decorate(cmd_like_: CommandLike) -> CommandLike:
            self.subcommands.append(cmd_like_)
            return cmd_like_

        return decorate

    def autocomplete(self, opt1: str, *opts: str) -> t.Callable[[AutocompleteCallbackT], AutocompleteCallbackT]:
        """
        Second order decorator that registers a function as an autocomplete callback for this command.

        The autocomplete callback **must** be an asynchronous function that takes exactly two arguments: ``option``
        (an instance of :obj:`hikari.interactions.command_interactions.AutocompleteInteractionOption`) which is
        the option being autocompleted, and ``interaction`` (an instance of :obj:`hikari.interactions.command_interactions.AutocompleteInteraction`)
        which is the interaction that triggered the autocomplete.

        Autocomplete can only be enabled for options with type :obj:`str`, :obj:`int`, or :obj:`float`.

        The callback should return one of the following: a single item of the option type, a sequence of items of the
        option type, a single :obj:`hikari.commands.CommandChoice`, or a sequence of :obj:`hikari.commands.CommandChoice`.

        Args:
            opt1 (:obj:`str`): Option that this callback will do autocomplete for.
            *opts (:obj:`str`): Additional options that this callback will do autocomplete for.
        """

        def decorate(func: AutocompleteCallbackT) -> AutocompleteCallbackT:
            for opt in [opt1, *opts]:
                self._autocomplete_callbacks[opt] = func
            return func

        return decorate


class SubCommandTrait(abc.ABC):
    """
    Trait that all subcommands and subgroups have.

    You can check if any given command is a subcommand by checking ``issubclass``
    on the command's class or ``isinstance`` if you have the object.
    """


class Command(abc.ABC):
    """
    Abstract base class for all command types.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the command is registered to.
        initialiser (:obj:`~CommandLike`): The ``CommandLike`` object to create the command from.
    """

    __slots__ = (
        "_initialiser",
        "_help_getter",
        "app",
        "callback",
        "name",
        "description",
        "options",
        "checks",
        "error_handler",
        "parent",
        "_plugin",
        "aliases",
        "parser",
        "cooldown_manager",
        "auto_defer",
        "default_ephemeral",
        "check_exempt",
        "hidden",
        "inherit_checks",
        "pass_options",
        "max_concurrency",
        "_max_concurrency_semaphores",
    )

    def __init__(self, app: app_.BotApp, initialiser: CommandLike) -> None:
        self._initialiser = initialiser
        self._help_getter = initialiser.help_getter
        self._plugin: t.Optional[plugins.Plugin] = None
        self.app: app_.BotApp = app
        """The ``BotApp`` instance the command is registered to."""
        self.callback: CommandCallbackT = initialiser.callback
        """The callback function for the command."""
        self.name: str = initialiser.name
        """The name of the command."""
        self.description: str = initialiser.description
        """The description of the command."""
        self.options: t.MutableMapping[str, OptionLike] = initialiser.options
        """The options for the command."""
        self.checks: t.Sequence[t.Union[checks.Check, checks._ExclusiveCheck]] = initialiser.checks
        """The checks for the command."""
        self.error_handler: t.Optional[
            t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]
        ] = initialiser.error_handler
        """The error handler function for the command."""
        self.parent: t.Optional[Command] = None
        """The parent for the command."""
        self.aliases: t.Sequence[str] = initialiser.aliases
        """The aliases for the command. This value means nothing for application commands."""
        self.parser: t.Optional[t.Type[parser_.BaseParser]] = initialiser.parser
        """The argument parser to use for prefix commands."""
        self.cooldown_manager: t.Optional[cooldowns.CooldownManager] = initialiser.cooldown_manager
        """The cooldown manager instance to use for the command."""
        self.auto_defer: bool = initialiser.auto_defer
        """Whether or not to automatically defer the response when the command is invoked."""
        self.default_ephemeral: bool = initialiser.ephemeral
        """Whether or not to send responses from this command as ephemeral messages by default."""
        self.check_exempt: t.Callable[
            [context_.base.Context], t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]
        ] = initialiser.check_exempt or (lambda _: False)
        """Check exempt predicate to use for the command."""
        self.hidden: bool = initialiser.hidden
        """Whether or not the command should be hidden from the help command."""
        self.inherit_checks: bool = initialiser.inherit_checks
        """Whether or not the command should inherit checks from the parent group."""
        self.pass_options: bool = initialiser.pass_options
        """Whether or not the command will have its options passed as keyword arguments when invoked."""
        self.max_concurrency: t.Optional[t.Tuple[int, t.Type[buckets.Bucket]]] = initialiser.max_concurrency
        """The max concurrency rule for the command."""
        self._max_concurrency_semaphores: t.Dict[t.Hashable, asyncio.Semaphore] = {}

    def __hash__(self) -> int:
        return hash(self.name)

    async def __call__(self, context: context_.base.Context, **kwargs: t.Any) -> None:
        if self.pass_options:
            for opt in context.raw_options:
                kwargs.setdefault(opt, context.raw_options[opt])
        return await self.callback(context, **kwargs)

    def _validate_attributes(self) -> None:
        pass

    def _set_plugin(self, pl: plugins.Plugin) -> None:
        self._plugin = pl

    @property
    def plugin(self) -> t.Optional[plugins.Plugin]:
        """The plugin that the command belongs to."""
        return self._plugin

    @plugin.setter
    def plugin(self, pl: plugins.Plugin) -> None:
        self._set_plugin(pl)

    @property
    def bot(self) -> app_.BotApp:
        """Alias for :obj:`~Context.app`"""
        return self.app

    def get_help(self, context: context_.base.Context) -> str:
        """
        Get the help text for the command under the given context. This method calls the help getter
        provided by the :obj:`~.decorators.set_help` decorator. An empty string will be returned
        if no help getter function was set.

        Args:
            context (:obj:`~.context.base.Context`): Context to get the help text under.

        Returns:
            :obj:`str`: Command's help text.
        """
        if self._help_getter is None:
            return ""
        return self._help_getter(self, context)

    @property
    def is_subcommand(self) -> bool:
        """Boolean representing whether or not this object is a subcommand."""
        return isinstance(self, SubCommandTrait)

    @property
    def qualname(self) -> str:
        """The qualified name for the command."""
        return self.name

    @property
    @abc.abstractmethod
    def signature(self) -> str:
        """The command's text signature."""
        ...

    async def _evaluate_max_concurrency(self, context: context_.base.Context) -> None:
        if self.max_concurrency is None:
            return
        bucket_hash = self.max_concurrency[1].extract_hash(context)
        if bucket_hash not in self._max_concurrency_semaphores:
            self._max_concurrency_semaphores[bucket_hash] = asyncio.Semaphore(self.max_concurrency[0])
        if self._max_concurrency_semaphores[bucket_hash].locked():
            assert context.invoked is not None
            raise errors.MaxConcurrencyLimitReached(
                f"Maximum concurrency limit for command '{context.invoked.qualname}' exceeded"
            )
        await self._max_concurrency_semaphores[bucket_hash].acquire()

    def _release_max_concurrency(self, context: context_.base.Context) -> None:
        if self.max_concurrency is None:
            return

        if sem := self._max_concurrency_semaphores.get(self.max_concurrency[1].extract_hash(context)):
            sem.release()

    async def invoke(self, context: context_.base.Context, **kwargs: t.Any) -> None:
        """
        Invokes the command under the given context. All checks, cooldowns and concurrency limits will be processed
        prior to invocation.
        """
        context._invoked = self

        await self._evaluate_max_concurrency(context)
        try:
            await self.evaluate_checks(context)
            await self.evaluate_cooldowns(context)
            await self(context, **kwargs)
        except Exception:
            raise
        finally:
            self._release_max_concurrency(context)

    async def evaluate_checks(self, context: context_.base.Context) -> bool:
        """
        Evaluate the command's checks under the given context. This method will either return
        ``True`` if all the checks passed or it will raise :obj:`~.errors.CheckFailure`.
        """
        exempt = self.check_exempt(context)
        if inspect.iscoroutine(exempt):
            exempt = await exempt
        if exempt:
            return True

        parent_checks = self.parent.checks if self.inherit_checks and self.parent is not None else []

        failed_checks: t.List[errors.CheckFailure] = []
        for check in [*self.app._checks, *getattr(self.plugin, "_checks", []), *self.checks, *parent_checks]:
            try:
                result = check(context)
                if inspect.iscoroutine(result):
                    result = await result

                if not result:
                    failed_checks.append(errors.CheckFailure(f"Check {check.__name__} failed for command {self.name}"))
            except Exception as ex:
                if not isinstance(ex, errors.CheckFailure):
                    error = errors.CheckFailure(str(ex))
                    error.__cause__ = ex
                else:
                    error = ex
                failed_checks.append(error)

        if len(failed_checks) > 1:
            raise errors.CheckFailure(
                "Multiple checks failed: " + ", ".join(str(ex) for ex in failed_checks), causes=failed_checks
            )
        elif failed_checks:
            raise failed_checks[0]

        return True

    async def evaluate_cooldowns(self, context: context_.base.Context) -> None:
        """
        Evaluate the command's cooldown under the given context. This method will either return
        ``None`` if the command is not on cooldown or raise :obj:`.errors.CommandIsOnCooldown`.
        """
        if self.cooldown_manager is not None:
            await self.cooldown_manager.add_cooldown(context)


class ApplicationCommand(Command, abc.ABC):
    """Abstract base class for all application command types."""

    __slots__ = ("_guilds", "instances")

    def __init__(self, app: app_.BotApp, initialiser: CommandLike) -> None:
        super().__init__(app, initialiser)
        self._guilds = initialiser.guilds
        self.instances: t.Dict[t.Union[int, None], hikari.PartialCommand] = {}
        """Mapping of guild ID to created hikari ``PartialCommand`` objects for this command."""

    @property
    def guilds(self) -> t.Sequence[int]:
        """The guilds that this command is available in."""
        return self.app.default_enabled_guilds if self._guilds is hikari.UNDEFINED else self._guilds

    @property
    def signature(self) -> str:
        sig = self.qualname
        if self.options:
            sig += f" {' '.join(f'<{o.name}>' if o.required else f'[{o.name}={o.default}]' for o in self.options.values())}"
        return sig

    async def create(self, guild: t.Optional[int] = None) -> hikari.PartialCommand:
        """
        Creates the command in the guild with the given ID, or globally if no
        guild ID was provided.

        Args:
            guild (Optional[:obj:`int`]): ID of the guild to create the command in, or ``None`` if to create globally.

        Returns:
            :obj:`~hikari.commands.PartialCommand`: Created hikari ``Command`` object.

        Notes:
            If creating a command globally, it will take up to 1 hour to appear and be usable. As mentioned in the
            `API documentation <https://discord.com/developers/docs/interactions/application-commands#making-a-global-command>`_
        """
        assert self.app.application is not None
        kwargs = self.as_create_kwargs()
        kwargs.update({"guild": guild} if guild is not None else {})

        cmd_type: hikari.CommandType = kwargs.pop("type")
        created_cmd: hikari.PartialCommand
        if cmd_type is hikari.CommandType.SLASH:
            created_cmd = await self.app.rest.create_slash_command(
                self.app.application,
                **kwargs,
            )
        else:
            created_cmd = await self.app.rest.create_context_menu_command(
                self.app.application,
                type=cmd_type,
                **kwargs,
            )

        self.instances[guild] = created_cmd
        assert isinstance(created_cmd, hikari.PartialCommand)
        return created_cmd

    async def _auto_create(self) -> None:
        if self.guilds:
            for guild_id in self.guilds:
                await self.create(guild_id)
        else:
            await self.create()

    async def delete(self, guild: t.Optional[int]) -> None:
        """
        Deletes the command in the guild with the given ID, or globally if no
        guild ID was provided.

        Args:
            guild (Optional[:obj:`int`]): ID of the guild to delete the command in, or ``None`` if to delete globally.

        Returns:
            ``None``
        """
        cmd = self.instances.pop(guild, None)
        if cmd is None:
            return
        await cmd.delete()

    async def _auto_delete(self) -> None:
        for cmd in self.instances.values():
            await cmd.delete()
        self.instances.clear()

    @abc.abstractmethod
    def as_create_kwargs(self) -> t.Dict[str, t.Any]:
        """
        Converts this class into a dictionary of kwargs required by
        :obj:`~hikari.api.rest.RESTClient.create_application_command`.

        Returns:
            Dict[:obj:`str`, Any]: Kwargs required in order to create the command.
        """
        ...
