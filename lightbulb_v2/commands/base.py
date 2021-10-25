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

__all__ = ["OptionLike", "CommandLike", "Command", "ApplicationCommand"]

import abc
import dataclasses
import inspect
import typing as t

import hikari

from lightbulb_v2 import errors

if t.TYPE_CHECKING:
    from lightbulb_v2 import app as app_
    from lightbulb_v2 import checks
    from lightbulb_v2 import context as context_
    from lightbulb_v2 import events
    from lightbulb_v2 import plugins

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


def _get_choice_objects_from_choices(
    choices: t.Sequence[t.Union[str, int, float, hikari.CommandChoice]]
) -> t.Sequence[hikari.CommandChoice]:
    return [c if isinstance(c, hikari.CommandChoice) else hikari.CommandChoice(name=str(c), value=c) for c in choices]


@dataclasses.dataclass
class OptionLike:
    """
    Generic dataclass representing a command option. Compatible with both prefix and application commands.
    """

    name: str
    """The name of the option."""
    description: str
    """The description of the option"""
    arg_type: t.Type[t.Any] = str
    """The type of the option."""
    required: bool = True
    """Whether or not the option is required. This will be inferred from whether or not a default value was provided if unspecified."""
    choices: t.Optional[t.Sequence[t.Union[str, int, float, hikari.CommandChoice]]] = None
    """The option's choices. This only affects application (slash) commands."""
    channel_types: t.Optional[t.Sequence[hikari.ChannelType]] = None
    """The channel types for this option. This only affects application (slash) commands."""
    default: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED
    """The default value for this option."""

    def as_application_command_option(self) -> hikari.CommandOption:
        """
        Convert this object into a :obj:`~hikari.commands.CommandOption`.

        Returns:
            :obj:`~hikari.commands.CommandOption`: Created ``CommandOption`` object.
        """
        kwargs: t.MutableMapping[str, t.Any] = {
            "type": OPTION_TYPE_MAPPING.get(self.arg_type, self.arg_type),
            "name": self.name,
            "description": self.description,
            "is_required": self.required,
        }
        if self.choices:
            kwargs["choices"] = _get_choice_objects_from_choices(self.choices)
        if self.channel_types:
            kwargs["channel_types"] = self.channel_types
        return hikari.CommandOption(**kwargs)


@dataclasses.dataclass
class CommandLike:
    """Generic dataclass representing a command. This can be converted into any command object."""

    callback: t.Callable[[context_.base.Context], t.Coroutine[t.Any, t.Any, None]]
    """The callback function for the command."""
    name: str
    """The name of the command."""
    description: str
    """The description of the command."""
    options: t.MutableMapping[str, OptionLike] = dataclasses.field(default_factory=dict)
    """The options for the command."""
    checks: t.Sequence[checks.Check] = dataclasses.field(default_factory=list)
    """The checks for the command."""
    cooldown_manager: t.Optional[...] = None  # TODO
    """The cooldown manager for the command."""
    error_handler: t.Optional[
        t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]
    ] = None
    """The error handler for the command."""
    aliases: t.Sequence[str] = dataclasses.field(default_factory=list)
    """The aliases for the command. This only affects prefix commands."""
    guilds: t.Sequence[int] = dataclasses.field(default_factory=list)
    """The guilds for the command. This only affects application commands."""
    subcommands: t.List[CommandLike] = dataclasses.field(default_factory=list)
    """Subcommands for the command."""

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


class Command(abc.ABC):
    """
    Abstract base class for all command types.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the command is registered to.
        initialiser (:obj:`~CommandLike`): The ``CommandLike`` object to create the command from.
    """

    def __init__(self, app: app_.BotApp, initialiser: CommandLike) -> None:
        self.app = app
        """The ``BotApp`` instance the command is registered to."""
        self.callback = initialiser.callback
        """The callback function for the command."""
        self.name = initialiser.name
        """The name of the command."""
        self.description = initialiser.description
        """The description of the command."""
        self.options = initialiser.options
        """The options for the command."""
        self.checks = initialiser.checks
        """The checks for the command."""
        self.cooldown_manager = initialiser.cooldown_manager
        """The cooldown manager for the command."""
        self.error_handler = initialiser.error_handler
        """The error handler function for the command."""
        self.parent: t.Optional[Command] = None
        """The parent for the command."""
        self.plugin: t.Optional[plugins.Plugin] = None
        """The plugin that the command belongs to."""

    async def __call__(self, context: context_.base.Context) -> None:
        return await self.callback(context)

    @property
    def is_subcommand(self) -> bool:
        """Whether or not the command is a subcommand."""
        return self.parent is not None

    @property
    def qualname(self) -> str:
        """The qualified name for the command."""
        return self.name

    @property
    @abc.abstractmethod
    def signature(self) -> str:
        """The command's text signature."""
        ...

    async def invoke(self, context: context_.base.Context) -> None:
        """
        Invokes the command under the given context. All checks and cooldowns will be processed
        prior to invocation.
        """
        await self.evaluate_checks(context)
        await self.evaluate_cooldowns(context)
        await self(context)

    async def evaluate_checks(self, context: context_.base.Context) -> bool:
        """
        Evaluate the command's checks under the given context. This method will either return
        ``True`` if all the checks passed or it will raise :obj:`~.errors.CheckFailure`.
        """
        failed_checks: t.List[errors.CheckFailure] = []
        for check in self.checks:
            try:
                result = check(context)
                if inspect.iscoroutine(result):
                    assert not isinstance(result, bool)
                    result = await result

                if not result:
                    failed_checks.append(errors.CheckFailure(f"Check {check.__name__} failed for command {self.name}"))
            except Exception as ex:
                error = errors.CheckFailure(str(ex))
                error.__cause__ = ex
                failed_checks.append(error)

        if len(failed_checks) > 1:
            raise errors.CheckFailure("Multiple checks failed: " + ", ".join(str(ex) for ex in failed_checks))
        elif failed_checks:
            raise failed_checks[0]

        return True

    async def evaluate_cooldowns(self, context: context_.base.Context) -> None:
        """
        Evaluate the command's cooldown under the given context. This method will either return
        ``None`` if the command is not on cooldown or raise :obj:`.errors.CommandIsOnCooldown`.
        """
        if self.cooldown_manager is not None:
            pass  # TODO


class ApplicationCommand(Command, abc.ABC):
    """Abstract base class for all application command types."""

    def __init__(self, app: app_.BotApp, initialiser: CommandLike) -> None:
        super().__init__(app, initialiser)
        self.guilds = initialiser.guilds
        """The guilds that this command is available in."""
        self.instances: t.Dict[t.Union[int, None], hikari.Command] = {}
        """Mapping of guild ID to created hikari ``Command`` objects for this command."""

    @property
    def signature(self) -> str:
        sig = f"/{self.qualname}"
        if self.options:
            sig += f" {' '.join(f'<{o.name}>' if o.required else f'[{o.name}]' for o in self.options.values())}"
        return sig

    async def create(self, guild: t.Optional[int] = None) -> hikari.Command:
        """
        Creates the command in the guild with the given ID, or globally if no
        guild ID was provided.

        Args:
            guild (Optional[:obj:`int`]): ID of the guild to create the command in, or ``None`` if to create globally.

        Returns:
            :obj:`~hikari.commands.Command`: Created hikari ``Command`` object.

        Notes:
            If creating a command globally, it will take up to 1 hour to appear and be usable. As mentioned in the
            `API documentation <https://discord.com/developers/docs/interactions/application-commands#making-a-global-command>`_
        """
        assert self.app.application is not None
        kwargs = self.as_create_kwargs()
        kwargs.update({"guild": guild} if guild is not None else {})
        created_cmd = await self.app.rest.create_application_command(
            self.app.application,
            **kwargs,
        )
        self.instances[guild] = created_cmd
        return created_cmd

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

    @abc.abstractmethod
    def as_create_kwargs(self) -> t.Dict[str, t.Any]:
        """
        Converts this class into a dictionary of kwargs required by
        :obj:`~hikari.api.rest.RESTClient.create_application_command`.

        Returns:
            Dict[:obj:`str`, Any]: Kwargs required in order to create the command.
        """
        ...
