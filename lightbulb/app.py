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

__all__ = ["BotApp", "when_mentioned_or"]

import asyncio
import collections.abc
import functools
import importlib
import inspect
import logging
import os
import pathlib
import re
import sys
import typing as t
from importlib import util

import hikari
from multidict import CIMultiDict

from lightbulb import checks
from lightbulb import commands
from lightbulb import context as context_
from lightbulb import decorators
from lightbulb import errors
from lightbulb import events
from lightbulb import help_command as help_command_
from lightbulb import internal
from lightbulb import parser
from lightbulb import plugins as plugins_
from lightbulb.utils import data_store

_LOGGER = logging.getLogger("lightbulb.app")
_APPLICATION_CMD_ERROR_REGEX: re.Pattern[str] = re.compile(
    r"https?://discord.com/api/v\d+/applications/\d+/guilds/(\d+)/commands"
)

PrefixT = t.Union[
    t.Sequence[str],
    t.Callable[["BotApp", hikari.Message], t.Union[t.Sequence[str], t.Coroutine[t.Any, t.Any, t.Sequence[str]]]],
]
CheckCoroT = t.TypeVar("CheckCoroT", bound=t.Callable[..., t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]])


class _ExtensionT(t.Protocol):
    def load(self, bot: BotApp) -> None:
        ...

    def unload(self, bot: BotApp) -> None:
        ...


APPLICATION_COMMANDS_EVENTS_MAPPING = {
    commands.slash.SlashCommand: (
        events.SlashCommandInvocationEvent,
        events.SlashCommandCompletionEvent,
        events.SlashCommandErrorEvent,
    ),
    commands.message.MessageCommand: (
        events.MessageCommandInvocationEvent,
        events.MessageCommandCompletionEvent,
        events.MessageCommandErrorEvent,
    ),
    commands.user.UserCommand: (
        events.UserCommandInvocationEvent,
        events.UserCommandCompletionEvent,
        events.UserCommandErrorEvent,
    ),
}


def when_mentioned_or(
    prefix_provider: PrefixT,
) -> t.Callable[[BotApp, hikari.Message], t.Coroutine[t.Any, t.Any, t.Sequence[str]]]:
    """
    Helper function which allows the bot's mentions to be used as the command prefix, as well
    as any other prefix(es) passed in or supplied by the ``prefix_provider``.

    Args:
        prefix_provider: A :obj:`str` prefix, Sequence[:obj:`str`] of prefixes, or sync or async callable that returns
            a prefix or sequence of prefixes. If ``None``, only the bot's mentions will be used.

    Example:

        .. code-block:: python

            # The below are all valid
            app = lightbulb.BotApp(prefix=lightbulb.when_mentioned_or("!"), ...)

            app = lightbulb.BotApp(prefix=lightbulb.when_mentioned_or(["!", "?"]), ...)

            # Using only mentions as the prefix
            app = lightbulb.BotApp(prefix=lightbulb.when_mentioned_or(None), ...)

            # Using with a get_prefix function
            def get_prefix(app, message):
                # Do something to get the prefixes
                return prefixes

            app = lightbulb.BotApp(prefix=lightbulb.when_mentioned_or(get_prefix), ...)
    """

    async def get_prefixes(app: BotApp, message: hikari.Message) -> t.Sequence[str]:
        me = app.get_me()
        assert me is not None
        mentions = [f"<@{me.id}> ", f"<@!{me.id}> "]

        if callable(prefix_provider):
            prefixes = prefix_provider(app, message)
            if inspect.iscoroutine(prefixes):
                prefixes = await prefixes
        else:
            prefixes = prefix_provider

        if isinstance(prefixes, str):
            return [*mentions, prefixes]
        elif isinstance(prefixes, t.Sequence):
            return mentions + list(prefixes)
        return mentions

    return get_prefixes


# str is by definition a sequence of str so these type hints are correct
def _default_get_prefix(_: BotApp, __: hikari.Message, *, prefixes: t.Sequence[str]) -> t.Sequence[str]:
    return prefixes


class BotApp(hikari.GatewayBot):
    """
    A subclassed implementation of the :obj:`~hikari.impl.gateway_bot.GatewayBot` class containing a command
    handler. This should be instantiated instead of the superclass if you wish to use the command
    handler implementation provided.

    Args:
        token (:obj:`str`): The bot account's token.
        prefix (Optional[PrefixT]): The command prefix to use for prefix commands, or ``None`` if prefix commands
            will not be used.
        ignore_bots (:obj:`bool`): Whether or not prefix commands should ignore bots for invocation. Defaults
            to ``True``.
        owner_ids (Sequence[:obj:`int`]): The IDs of the users that own the bot. If not provided then it will be fetched
            by :obj:`~BotApp.fetch_owner_ids`.
        default_enabled_guilds (Union[:obj:`int`, Sequence[:obj:`int`]]): The guild(s) to create application commands
            in by default if no guilds are specified per-command. Defaults to an empty tuple.
        help_class (Optional[Type[:obj:`~.help_command.BaseHelpCommand`]]): Class to use for the bot's help command.
            Defaults to :obj:`~.help_command.DefaultHelpCommand`. If ``None``, no help command will be added
            to the bot by default.
        help_slash_command (:obj:`bool`): Whether or not the help command should be implemented as a slash command
            as well as a prefix command. Defaults to ``False``.
        delete_unbound_commands (:obj:`bool`): Whether or not the bot should delete application commands that it cannot
            find an implementation for when the bot starts. Defaults to ``True``.
        case_insensitive_prefixes (:obj:`bool`): Wheter or not command prefixes should be case-insensitive.
            Defaults to ``False``.
        case_insensitive_prefix_commands (:obj:`bool`): Whether or not prefix command names should be case-insensitive.
            Defaults to ``False``.
        **kwargs (Any): Additional keyword arguments passed to the constructor of the :obj:`~hikari.impl.gateway_bot.GatewayBot`
            class.
    """  # noqa: E501 (line-too-long)

    __slots__ = (
        "get_prefix",
        "ignore_bots",
        "owner_ids",
        "application",
        "d",
        "_prefix_commands",
        "_slash_commands",
        "_message_commands",
        "_user_commands",
        "_plugins",
        "_checks",
        "extensions",
        "_current_extension",
        "default_enabled_guilds",
        "_help_command",
        "_delete_unbound_commands",
        "_case_insensitive_prefixes",
        "_case_insensitive_prefix_commands",
        "_running_tasks",
    )

    def __init__(
        self,
        token: str,
        prefix: t.Optional[PrefixT] = None,
        ignore_bots: bool = True,
        owner_ids: t.Sequence[int] = (),
        default_enabled_guilds: t.Union[int, t.Sequence[int]] = (),
        help_class: t.Optional[t.Type[help_command_.BaseHelpCommand]] = help_command_.DefaultHelpCommand,
        help_slash_command: bool = False,
        delete_unbound_commands: bool = True,
        case_insensitive_prefixes: bool = False,
        case_insensitive_prefix_commands: bool = False,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(token, **kwargs)
        # The prefix command handler expects an iterable to be returned from the get_prefix function,
        # so we have to wrap a single string prefix in a list here.
        if prefix is not None:
            prefix = [prefix] if isinstance(prefix, str) else prefix
            if isinstance(prefix, t.Sequence):
                # Create the default get prefix from the passed-in prefixes if a get_prefix function
                # was not provided
                prefix = functools.partial(_default_get_prefix, prefixes=prefix)
            self.get_prefix: t.Callable[
                [BotApp, hikari.Message], t.Union[t.Sequence[str], t.Coroutine[t.Any, t.Any, t.Sequence[str]]]
            ] = prefix

        self._delete_unbound_commands = delete_unbound_commands
        self._case_insensitive_prefixes = case_insensitive_prefixes
        self._case_insensitive_prefix_commands = case_insensitive_prefix_commands

        self.ignore_bots: bool = ignore_bots
        """Whether or not other bots will be ignored when invoking prefix commands."""
        self.owner_ids: t.Sequence[int] = owner_ids
        """The owner ID(s) for the owner(s) of the bot account."""
        self.default_enabled_guilds: t.Sequence[int] = (
            (default_enabled_guilds,) if isinstance(default_enabled_guilds, int) else default_enabled_guilds
        )
        """The default guilds that application commands will be enabled in."""

        self.application: t.Optional[hikari.Application] = None
        """The :obj:`~hikari.applications.Application` for the bot account.
        This will always be ``None`` before the bot has logged in."""

        self.d: data_store.DataStore = data_store.DataStore()
        """A :obj:`~.utils.data_store.DataStore` instance enabling storage of custom data without subclassing."""

        self.extensions: t.List[str] = []
        """A list of the currently loaded extensions."""
        self._current_extension: t.Optional[_ExtensionT] = None

        self._prefix_commands: t.MutableMapping[str, commands.prefix.PrefixCommand] = (
            {} if not case_insensitive_prefix_commands else CIMultiDict()  # type: ignore
        )
        self._slash_commands: t.MutableMapping[str, commands.slash.SlashCommand] = {}
        self._message_commands: t.MutableMapping[str, commands.message.MessageCommand] = {}
        self._user_commands: t.MutableMapping[str, commands.user.UserCommand] = {}

        self._plugins: t.MutableMapping[str, plugins_.Plugin] = {}

        self._checks: t.List[t.Union[checks.Check, checks._ExclusiveCheck]] = []

        self._help_command: t.Optional[help_command_.BaseHelpCommand] = None
        if help_class is not None:
            help_cmd_types: t.List[t.Type[commands.base.Command]] = []

            if prefix is not None:
                help_cmd_types.append(commands.prefix.PrefixCommand)

            if help_slash_command:
                help_cmd_types.append(commands.slash.SlashCommand)

            if help_cmd_types:
                self._help_command = help_class(self)

                @decorators.option(
                    "obj", "Object to get help for", required=False, modifier=commands.base.OptionModifier.CONSUME_REST
                )
                @decorators.command("help", "Get help information for the bot", auto_defer=True)
                @decorators.implements(*help_cmd_types)
                async def __default_help(ctx: context_.base.Context) -> None:
                    assert self._help_command is not None
                    await self._help_command.send_help(ctx, ctx.options.obj)

                self.command(__default_help)

        # We need to store created tasks internally to ensure that they do not
        # get destroyed mid-execution. See asyncio.create_task documentation for more.
        self._running_tasks: t.List[asyncio.Task[t.Any]] = []

        if prefix is not None:
            self.subscribe(hikari.MessageCreateEvent, self.handle_message_create_for_prefix_commands)
        self.subscribe(hikari.StartedEvent, self._manage_application_commands)
        self.subscribe(hikari.InteractionCreateEvent, self.handle_interaction_create_for_application_commands)
        self.subscribe(hikari.InteractionCreateEvent, self.handle_interaction_create_for_autocomplete)

    def create_task(self, coro: t.Awaitable[t.Any], *, name: t.Optional[str] = None) -> asyncio.Task[t.Any]:
        """
        Wrap the given awaitable into an :obj:`asyncio.Task` and schedule its execution. This
        method functions the same as :meth:`asyncio.create_task`, but keeps a reference to the task
        alive until execution is completed to ensure the task is not destroyed mid-execution.

        Args:
            coro (Awaitable[Any]): Coroutine to wrap into a task.

        Keyword Args:
            name (Optional[:obj:`str`]): The name of the task. Not required, defaults to ``None``.

        Returns:
            :obj:`asyncio.Task`: Created task object.

        .. versionadded:: 2.2.0
        """
        task: asyncio.Task[None] = asyncio.create_task(coro, name=name)  # type: ignore[arg-type]
        self._running_tasks.append(task)
        task.add_done_callback(lambda task_: self._running_tasks.remove(task_))
        return task

    @property
    def help_command(self) -> t.Optional[help_command_.BaseHelpCommand]:
        """The current help command instance registered to the bot."""
        return self._help_command

    @help_command.setter
    def help_command(self, val: help_command_.BaseHelpCommand) -> None:
        self._help_command = val

    @property
    def prefix_commands(self) -> t.MutableMapping[str, commands.prefix.PrefixCommand]:
        """Mapping of command name to command object containing all prefix commands registered to the bot."""
        return self._prefix_commands

    @property
    def slash_commands(self) -> t.MutableMapping[str, commands.slash.SlashCommand]:
        """Mapping of command name to command object containing all slash commands registered to the bot."""
        return self._slash_commands

    @property
    def message_commands(self) -> t.MutableMapping[str, commands.message.MessageCommand]:
        """Mapping of command name to command object containing all message commands registered to the bot."""
        return self._message_commands

    @property
    def user_commands(self) -> t.MutableMapping[str, commands.user.UserCommand]:
        """Mapping of command name to command object containing all user commands registered to the bot."""
        return self._user_commands

    @property
    def plugins(self) -> t.MutableMapping[str, plugins_.Plugin]:
        """Mapping of plugin name to plugin object containing all plugins registered to the bot."""
        return self._plugins

    def _add_command_to_correct_attr(self, command: commands.base.Command) -> None:
        if isinstance(command, commands.prefix.PrefixCommand):
            for item in [command.name, *command.aliases]:
                if item in self._prefix_commands:
                    raise errors.CommandAlreadyExists(
                        f"A prefix command with name or alias {item!r} is already registered."
                    )
            for item in [command.name, *command.aliases]:
                self._prefix_commands[item] = command
        elif isinstance(command, commands.slash.SlashCommand):
            if command.name in self._slash_commands:
                raise errors.CommandAlreadyExists(f"A slash command with name {command.name!r} is already registered.")
            self._slash_commands[command.name] = command
        elif isinstance(command, commands.message.MessageCommand):
            if command.name in self._message_commands:
                raise errors.CommandAlreadyExists(
                    f"A message command with name {command.name!r} is already registered."
                )
            self._message_commands[command.name] = command
        elif isinstance(command, commands.user.UserCommand):
            if command.name in self._user_commands:
                raise errors.CommandAlreadyExists(f"A user command with name {command.name!r} is already registered.")
            self._user_commands[command.name] = command

    def _get_application_command(
        self, interaction: hikari.CommandInteraction
    ) -> t.Optional[commands.base.ApplicationCommand]:
        if interaction.command_type is hikari.CommandType.SLASH:
            return self.get_slash_command(interaction.command_name)
        elif interaction.command_type is hikari.CommandType.USER:
            return self.get_user_command(interaction.command_name)
        elif interaction.command_type is hikari.CommandType.MESSAGE:
            return self.get_message_command(interaction.command_name)
        return None

    async def _manage_application_commands(self, _: hikari.StartingEvent) -> None:
        if self.application is None:
            self.application = await self.rest.fetch_application()

        try:
            await internal.manage_application_commands(self)
        except hikari.ForbiddenError as exc:
            error_msg = str(exc)
            match = _APPLICATION_CMD_ERROR_REGEX.search(error_msg)
            guild_id = "unknown" if match is None else match.group(1)
            raise errors.ApplicationCommandCreationFailed(
                f"Application command creation failed for guild {guild_id!r}. "
                + "Is your bot in the guild and was it invited with the 'applications.commands' scope?"
            ) from exc
        finally:
            await self.dispatch(events.LightbulbStartedEvent(app=self))

    async def sync_application_commands(self) -> None:
        """
        Sync all application commands registered to the bot with discord.

        Returns:
            ``None``

        .. versionadded:: 2.2.0
        """
        await internal.manage_application_commands(self)

    @staticmethod
    def _get_events_for_application_command(
        command: commands.base.ApplicationCommand,
    ) -> t.Tuple[
        t.Type[events.CommandInvocationEvent], t.Type[events.CommandCompletionEvent], t.Type[events.CommandErrorEvent]
    ]:
        for k in APPLICATION_COMMANDS_EVENTS_MAPPING:
            if isinstance(command, k):
                return APPLICATION_COMMANDS_EVENTS_MAPPING[k]
        raise TypeError("Application command type not recognised")

    def print_banner(  # type: ignore[override]
        self,
        banner: t.Optional[str],
        allow_color: bool,
        force_color: bool,
        extra_args: t.Optional[t.Dict[str, str]] = None,
    ) -> None:
        super().print_banner(banner, allow_color, force_color)
        if banner == "hikari":
            sys.stdout.write("Thank you for using lightbulb!\n")

    def load_extensions(self, *extensions: str) -> None:
        """
        Load external extension(s) into the bot. Extension name follows the format ``<directory>.<filename>``
        Each extension **must** contain a function ``load`` which takes a single argument which will be the
        ``BotApp`` instance you are loading the extension into.

        Args:
            extensions (:obj:`str`): The name of the extension(s) to load.

        Returns:
            ``None``

        Raises:
            :obj:`~.errors.ExtensionAlreadyLoaded`: If the extension has already been loaded.
            :obj:`~.errors.ExtensionMissingLoad`: If the extension to be loaded does not contain a ``load`` function.
            :obj:`~.errors.ExtensionNotFound`: If the extension to be loaded does not exist.
        """
        if len(extensions) > 1 or not extensions:
            for extension in extensions:
                self.load_extensions(extension)
            return
        extension = extensions[0]

        if extension in self.extensions:
            raise errors.ExtensionAlreadyLoaded(f"Extension {extension!r} is already loaded.")

        spec = util.find_spec(extension)
        if spec is None:
            raise errors.ExtensionNotFound(f"No extension by the name {extension!r} was found")

        module = importlib.import_module(extension)

        ext = t.cast(_ExtensionT, module)
        self._current_extension = ext

        if not hasattr(module, "load"):
            raise errors.ExtensionMissingLoad(f"Extension {extension!r} is missing a load function")
        else:
            ext.load(self)
            self.extensions.append(extension)
            _LOGGER.info("Extension loaded %r", extension)
        self._current_extension = None

    def unload_extensions(self, *extensions: str) -> None:
        """
        Unload external extension(s) from the bot. This method relies on a function, ``unload``
        existing in the extensions which the bot will use to remove all commands and/or plugins
        from the bot.

        Args:
            extensions (:obj:`str`): The name of the extension(s) to unload.

        Returns:
            ``None``

        Raises:
            :obj:`~.errors.ExtensionNotLoaded`: If the extension has not been loaded.
            :obj:`~.errors.ExtensionMissingUnload`: If the extension does not contain an ``unload`` function.
            :obj:`~.errors.ExtensionNotFound`: If the extension to be unloaded does not exist.
        """
        if len(extensions) > 1 or not extensions:
            for extension in extensions:
                self.unload_extensions(extension)
            return
        extension = extensions[0]

        if extension not in self.extensions:
            raise errors.ExtensionNotLoaded(f"Extension {extension!r} is not loaded.")

        try:
            module = importlib.import_module(extension)
        except ModuleNotFoundError:
            raise errors.ExtensionNotFound(f"No extension by the name {extension!r} was found") from None

        ext = t.cast(_ExtensionT, module)
        self._current_extension = ext

        if not hasattr(module, "unload"):
            raise errors.ExtensionMissingUnload(f"Extension {extension!r} is missing an unload function")
        else:
            ext.unload(self)
            self.extensions.remove(extension)
            del sys.modules[extension]
            _LOGGER.info("Extension unloaded %r", extension)
        self._current_extension = None

    def reload_extensions(self, *extensions: str) -> None:
        """
        Reload bot extension(s). This method is atomic and so the bot will
        revert to the previous loaded state if an extension encounters a problem
        during unloading or loading.

        Args:
            extensions (:obj:`str`): The name of the extension(s) to be reloaded.

        Returns:
            ``None``
        """
        if len(extensions) > 1 or not extensions:
            for extension in extensions:
                self.reload_extensions(extension)
            return
        extension = extensions[0]
        try:
            old = sys.modules[extension]
        except KeyError:
            raise errors.ExtensionNotLoaded(f"Extension {extension!r} is not loaded.")
        try:
            self.unload_extensions(extension)
            self.load_extensions(extension)
        except Exception as e:
            sys.modules[extension] = old
            if not isinstance(e, errors.ExtensionAlreadyLoaded):
                self.load_extensions(extension)
            raise e
        else:
            del old

    def load_extensions_from(
        self, *paths: t.Union[str, pathlib.Path], recursive: bool = False, must_exist: bool = True
    ) -> None:
        """
        Load all external extensions from the given directories. Files that begin with an underscore ( _ ) are ignored.
        Every extension **must** contain a function ``load`` which takes a single argument which will be the ``BotApp``
        instance you are loading the extension into.

        Args:
            *paths (Union[:obj:`str`, :obj:`pathlib.Path`]): The directories to load extensions from. These can be
                relative or absolute directories. In the case that a directory is absolute, the extension name will
                be set as though the directory was relative.

        Keyword Args:
            recursive (:obj:`bool`): Whether to search the directories recursively. Defaults to False.
            must_exist (:obj:`bool`): Whether all directories must exist before extensions can be loaded. If this is
                False and a directory does not exist, the directory will be ignored. If this is True, a
                :obj:`FileNotFoundError` is thrown if any directory does not exist. Defaults to True.

        Returns:
            ``None``

        Raises:
            :obj:`~.errors.ExtensionAlreadyLoaded`: If the extension has already been loaded.
            :obj:`~.errors.ExtensionMissingLoad`: If the extension to be loaded does not contain a ``load`` function.
            :obj:`~.errors.ExtensionNotFound`: If the extension to be loaded does not exist.
            :obj:`FileNotFoundError`: If any directory to load extensions from does not exist and ``must_exist``
                is True.
            :obj:`ValueError`: If the path provided is not relative to the current working directory.
        """
        if len(paths) > 1 or not paths:
            for path_ in paths:
                self.load_extensions_from(path_, recursive=recursive, must_exist=must_exist)
            return

        path = paths[0]

        if isinstance(path, str):
            path = pathlib.Path(path)

        try:
            path = path.resolve().relative_to(pathlib.Path.cwd())
        except ValueError:
            raise ValueError(f"'{path}' must be relative to the working directory") from None

        if not path.is_dir():
            if must_exist:
                raise FileNotFoundError(f"'{path}' is not an existing directory")
            return

        glob = path.rglob if recursive else path.glob
        for ext_path in glob("[!_]*.py"):
            ext = str(ext_path.with_suffix("")).replace(os.sep, ".")
            self.load_extensions(ext)

    async def fetch_owner_ids(self) -> t.Sequence[hikari.Snowflakeish]:
        """
        Fetch the bot's owner IDs, or return the given owner IDs on instantiation if provided.

        Returns:
            Sequence[Snowflakeish]: The IDs of the bot's owners.
        """
        if self.owner_ids:
            return self.owner_ids

        self.application = self.application or await self.rest.fetch_application()

        owner_ids: t.List[hikari.Snowflake] = []
        if self.application.owner is not None:
            owner_ids.append(self.application.owner.id)
        if self.application.team is not None:
            owner_ids.extend(member_id for member_id in self.application.team.members)
        return owner_ids

    async def maybe_dispatch_error_event(  # noqa: D417 (undocumented-param)
        self,
        event: events.CommandErrorEvent,
        priority_handlers: t.Sequence[
            t.Union[None, t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]]
        ],
    ) -> bool:
        """
        Attempts to handle the event first using the given ``priority_handlers``, falling back to dispatching
        the given event to global listeners.

        Args:
            event (:obj:`~.events.CommandErrorEvent`): Event to attempt to handle.
            priority_handlers (Sequence[Union[``None``, ListenerT)]]: Handlers to attempt to use to handle the
                event before falling back to global event listeners.

        Returns:
            :obj:`bool`: Whether or not the given event was handled or dispatched successfully.
        """
        handled = False
        for listener in priority_handlers:
            if handled:
                break
            if listener is not None:
                handled = bool(await listener(event))

        if not handled and (
            self.get_listeners(type(event), polymorphic=True)
            or self.get_listeners(events.CommandErrorEvent, polymorphic=True)
        ):
            await self.dispatch(event)
            handled = True

        return handled

    @t.overload
    def check(self, check: t.Union[checks.Check, CheckCoroT]) -> checks.Check:
        ...

    @t.overload
    def check(self) -> t.Callable[[CheckCoroT], checks.Check]:
        ...

    def check(
        self,
        check: t.Optional[t.Union[checks.Check, CheckCoroT, checks._ExclusiveCheck]] = None,
    ) -> t.Union[checks.Check, t.Callable[[CheckCoroT], checks.Check]]:
        """
        Adds a :obj:`~.checks.Check` object or check function the bot's checks. This method can be used as a
        first or second order decorator, or called manually with the :obj:`~.checks.Check` instance or function to
        add as a check. If a function is decorated or passed in then it will be wrapped in a :obj:`~.checks.Check`
        object before it is added to the bot.
        """
        if check is not None:
            if not isinstance(check, checks.Check):
                check = checks.Check(check)
            self._checks.append(check)

            check.add_to_object_hook(self)

            return check

        def decorate(
            check_func: t.Callable[[context_.base.Context], t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]],
        ) -> checks.Check:
            new_check = checks.Check(check_func)
            self._checks.append(new_check)

            new_check.add_to_object_hook(self)

            return new_check

        return decorate

    def get_prefix_command(self, name: str) -> t.Optional[commands.prefix.PrefixCommand]:
        """
        Gets the prefix command with the given name, or ``None`` if no command with that name was found.

        Args:
            name (:obj:`str`): Name of the prefix command to get.

        Returns:
            Optional[:obj:`~.commands.prefix.PrefixCommand`]: Prefix command object with the given name, or ``None``
                if not found.
        """
        parts = name.split()
        if len(parts) == 1:
            return self._prefix_commands.get(name)

        maybe_group = self._prefix_commands.get(parts.pop(0))
        if not isinstance(maybe_group, commands.prefix.PrefixCommandGroup):
            return None

        this: t.Optional[
            t.Union[
                commands.prefix.PrefixCommandGroup, commands.prefix.PrefixSubGroup, commands.prefix.PrefixSubCommand
            ]
        ] = maybe_group
        for part in parts:
            if this is None or isinstance(this, commands.prefix.PrefixSubCommand):
                return None
            this = this.get_subcommand(part)

        return this

    def get_slash_command(self, name: str) -> t.Optional[commands.slash.SlashCommand]:
        """
        Gets the slash command with the given name, or ``None`` if no command with that name was found.

        Args:
            name (:obj:`str`): Name of the slash command to get.

        Returns:
            Optional[:obj:`~.commands.slash.SlashCommand`]: Slash command object with the given name, or ``None``
                if not found.
        """
        return self._slash_commands.get(name)

    def get_message_command(self, name: str) -> t.Optional[commands.message.MessageCommand]:
        """
        Gets the message command with the given name, or ``None`` if no command with that name was found.

        Args:
            name (:obj:`str`): Name of the message command to get.

        Returns:
            Optional[:obj:`~.commands.message.MessageCommand`]: Message command object with the given name, or ``None``
                if not found.
        """
        return self._message_commands.get(name)

    def get_user_command(self, name: str) -> t.Optional[commands.user.UserCommand]:
        """
        Gets the user command with the given name, or ``None`` if no command with that name was found.

        Args:
            name (:obj:`str`): Name of the user command to get.

        Returns:
            Optional[:obj:`~.commands.user.UserCommand`]: User command object with the given name, or ``None``
                if not found.
        """
        return self._user_commands.get(name)

    @t.overload
    def command(self, cmd_like: commands.base.CommandLike) -> commands.base.CommandLike:
        ...

    @t.overload
    def command(self) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
        ...

    def command(
        self, cmd_like: t.Optional[commands.base.CommandLike] = None
    ) -> t.Union[commands.base.CommandLike, t.Callable[[commands.base.CommandLike], commands.base.CommandLike]]:
        """
        Adds a :obj:`~.commands.base.CommandLike` object as a command to the bot. This method can be used as a
        first or second order decorator, or called manually with the :obj:`~.commands.CommandLike` instance to
        add as a command.
        """
        if cmd_like is not None:
            commands_to_impl: t.Sequence[t.Type[commands.base.Command]] = getattr(
                cmd_like.callback, "__cmd_types__", []
            )
            _LOGGER.debug(
                "Registering command %r. Requested types are: %s",
                cmd_like.name,
                ",".join(c.__name__ for c in commands_to_impl),
            )
            for command_cls in commands_to_impl:
                cmd = command_cls(self, cmd_like)

                if cmd.is_subcommand:
                    continue

                cmd._validate_attributes()

                self._add_command_to_correct_attr(cmd)
            return cmd_like

        def decorate(cmd_like_: commands.base.CommandLike) -> commands.base.CommandLike:
            self.command(cmd_like_)
            return cmd_like_

        return decorate

    def remove_command(self, command: t.Union[commands.base.Command, commands.base.CommandLike]) -> None:
        """
        Removes a command or command-like object from the bot.

        Args:
            command (Union[:obj:`~.commands.base.Command`, :obj:`~.commands.base.CommandLike`): Command or
                command-like object to remove from the bot.

        Returns:
            ``None``
        """
        _LOGGER.debug("Removing command %r (%s)", command.name, command.__class__.__name__)
        if isinstance(command, commands.base.CommandLike):
            self._remove_commandlike(command)
            return

        if isinstance(command, commands.prefix.PrefixCommand):
            for item in [command.name, *command.aliases]:
                self._prefix_commands.pop(item, None)
        elif isinstance(command, commands.slash.SlashCommand):
            self._slash_commands.pop(command.name, None)
        elif isinstance(command, commands.message.MessageCommand):
            self._message_commands.pop(command.name, None)
        elif isinstance(command, commands.user.UserCommand):
            self._user_commands.pop(command.name, None)

    def _remove_commandlike(self, cmd_like: commands.base.CommandLike) -> None:
        commands_to_remove: t.List[t.Optional[commands.base.Command]] = []
        cmd_types: t.Sequence[t.Type[commands.base.Command]] = getattr(cmd_like.callback, "__cmd_types__", [])
        for cmd_type in cmd_types:
            if issubclass(cmd_type, commands.prefix.PrefixCommand):
                commands_to_remove.append(self.get_prefix_command(cmd_like.name))
            elif issubclass(cmd_type, commands.slash.SlashCommand):
                commands_to_remove.append(self.get_slash_command(cmd_like.name))
            elif issubclass(cmd_type, commands.message.MessageCommand):
                commands_to_remove.append(self.get_message_command(cmd_like.name))
            elif issubclass(cmd_type, commands.user.UserCommand):
                commands_to_remove.append(self.get_user_command(cmd_like.name))

        for command in filter(None, commands_to_remove):
            self.remove_command(command)

    def get_plugin(self, name: str) -> t.Optional[plugins_.Plugin]:
        """
        Gets the plugin with the given name, or ``None`` if no plugin with that name was found.

        Args:
            name (:obj:`str`): Name of the plugin to get.

        Returns:
            Optional[:obj:`~.plugins.Plugin`]: Plugin object with the given name, or ``None`` if not found.
        """
        return self._plugins.get(name)

    def add_plugin(self, plugin: plugins_.Plugin) -> None:
        """
        Registers a plugin to the bot, adding all commands and listeners present
        in the plugin.

        Args:
            plugin (:obj:`~.plugins.Plugin`): Plugin to register to the bot.

        Returns:
            ``None``
        """
        plugin.app = self
        for command in plugin._all_commands:
            self._add_command_to_correct_attr(command)
        for event, listeners in plugin._listeners.items():
            for listener in listeners:
                self.subscribe(event, listener)
        _LOGGER.debug("Plugin registered %r", plugin.name)
        self._plugins[plugin.name] = plugin

    def remove_plugin(self, plugin_or_name: t.Union[plugins_.Plugin, str]) -> None:
        """
        Unregisters a plugin from the bot, removing all commands and listeners
        present in the plugin.

        Args:
            plugin_or_name (Union[:obj:`~.plugins.Plugin`, :obj:`str`]): Plugin or name of the plugin
                to unregister from the bot.

        Returns:
            ``None``
        """
        plugin: t.Optional[t.Union[plugins_.Plugin, str]] = plugin_or_name
        if isinstance(plugin, str):
            plugin = self.get_plugin(plugin)

        if plugin is None:
            return

        assert isinstance(plugin, plugins_.Plugin)

        for command in plugin._raw_commands:
            self.remove_command(command)
        for event, listeners in plugin._listeners.items():
            for listener in listeners:
                self.unsubscribe(event, listener)

        if plugin._remove_hook is not None:
            maybe_coro = plugin._remove_hook()
            if inspect.iscoroutine(maybe_coro):
                self.create_task(maybe_coro)

        self._plugins.pop(plugin.name, None)
        _LOGGER.debug("Plugin removed %r", plugin.name)

    async def purge_application_commands(self, *guild_ids: hikari.Snowflakeish, global_commands: bool = False) -> None:
        """
        Purges all application commands from the guilds with the specified IDs, and all the global application
        commands if ``global_commands`` is ``True``. Useful if you want to teardown old slash commands from
        the bot and cannot be bothered to fetch them individually yourself. If neither `guild_ids` nor `global_commands`
        is specified then this method will do nothing.

        Args:
            *guild_ids (:obj:`hikari.Snowflakeish`): IDs for the guilds to purge application commands from.

        Keyword Args:
            global_commands (:obj:`bool`): Whether or not to purge global slash commands from the bot.

        Returns:
            ``None``
        """
        assert self.application is not None
        if global_commands:
            await self.rest.set_application_commands(self.application, ())
        if guild_ids:
            for guild_id in guild_ids:
                await self.rest.set_application_commands(self.application, (), guild_id)

    async def get_prefix_context(
        self,
        event: hikari.MessageCreateEvent,
        cls: t.Type[context_.prefix.PrefixContext] = context_.prefix.PrefixContext,
    ) -> t.Optional[context_.prefix.PrefixContext]:
        """
        Get the :obj:`~.context.prefix.PrefixContext` instance for the given event, or ``None`` if
        no context could be created.

        Args:
            event (:obj:`~hikari.events.message_events.MessageCreateEvent`): Event to get the prefix context for.
            cls (Type[:obj:`~.context.prefix.PrefixContext`]): Context class to instantiate. Defaults to
                :obj:`~.context.prefix.PrefixContext`.

        Returns:
            Optional[:obj:`~.context.prefix.PrefixContext`]: Prefix context instance for the given event.
        """
        assert event.message.content is not None

        prefixes = self.get_prefix(self, event.message)
        if inspect.iscoroutine(prefixes):
            prefixes = await prefixes
        prefixes = t.cast(t.Sequence[str], prefixes)

        if isinstance(prefixes, str):
            prefixes = (prefixes,)

        message = event.message.content
        if self._case_insensitive_prefixes:
            message = message.lower()
            prefixes = tuple(map(str.lower, prefixes))

        prefixes = sorted(prefixes, key=len, reverse=True)

        invoked_prefix = None
        for prefix in prefixes:
            if message.startswith(prefix):
                invoked_prefix = prefix
                break

        if invoked_prefix is None:
            return None

        new_content = event.message.content[len(invoked_prefix) :]
        if not new_content or new_content.isspace():
            return None

        split_content = new_content.split(maxsplit=1)
        invoked_with, args = split_content[0], "".join(split_content[1:])

        if not invoked_with:
            return None

        command = self.get_prefix_command(invoked_with)
        ctx = cls(self, event, command, invoked_with, invoked_prefix)
        if ctx.command is not None:
            ctx._parser = (ctx.command.parser or parser.Parser)(ctx, args)
        return ctx

    async def process_prefix_commands(self, context: context_.prefix.PrefixContext) -> None:
        """
        Invokes the appropriate command for the given context.

        Args:
            context (:obj:`.context.prefix.PrefixContext`): Context to invoke the command under.

        Returns:
            ``None``
        """
        if context.command is None:
            raise errors.CommandNotFound(
                f"A command with name or alias {context.invoked_with!r} does not exist",
                invoked_with=context.invoked_with,
            )

        await context.invoke()

    async def handle_message_create_for_prefix_commands(self, event: hikari.MessageCreateEvent) -> None:
        """
        Prefix command :obj:`~hikari.events.message_events.MessageCreateEvent` listener. This handles fetching the
        context, dispatching events, and invoking the appropriate command.

        Args:
            event (:obj:`~hikari.events.message_events.MessageCreateEvent`): Event that prefix commands will be
                processed for.

        Returns:
            ``None``
        """
        if self.ignore_bots and not event.is_human:
            return

        if not event.message.content:
            return

        context = await self.get_prefix_context(event)
        if context is None:
            return

        if context.command is not None:
            await self.dispatch(events.PrefixCommandInvocationEvent(app=self, command=context.command, context=context))

        try:
            await self.process_prefix_commands(context)
        except Exception as exc:
            new_exc = exc
            if not isinstance(exc, errors.LightbulbError):
                assert context.command is not None
                new_exc = errors.CommandInvocationError(
                    f"An error occurred during command {context.command.name!r} invocation", original=exc
                )
            assert isinstance(new_exc, errors.LightbulbError)
            error_event = events.PrefixCommandErrorEvent(app=self, exception=new_exc, context=context)
            handled = await self.maybe_dispatch_error_event(
                error_event,
                [
                    getattr(context.command, "error_handler", None),
                    getattr(context.command.plugin, "_error_handler", None) if context.command is not None else None,
                ],
            )

            if not handled:
                raise new_exc
        else:
            assert context.command is not None
            await self.dispatch(events.PrefixCommandCompletionEvent(app=self, command=context.command, context=context))

    async def get_slash_context(
        self,
        event: hikari.InteractionCreateEvent,
        command: commands.slash.SlashCommand,
        cls: t.Type[context_.slash.SlashContext] = context_.slash.SlashContext,
    ) -> context_.slash.SlashContext:
        """
        Get the :obj:`~.context.slash.SlashContext` instance for the given event.

        Args:
            event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): Event to get the slash context for.
            command (:obj:`~.commands.slash.SlashCommand`): Command that the context is for.
            cls (Type[:obj:`~.context.slash.SlashContext`]): Context class to instantiate. Defaults to
                :obj:`~.context.slash.SlashContext`.

        Returns:
            :obj:`~.context.slash.SlashContext`: Slash context instance for the given event.
        """
        return cls(self, event, command)

    async def get_message_context(
        self,
        event: hikari.InteractionCreateEvent,
        command: commands.message.MessageCommand,
        cls: t.Type[context_.message.MessageContext] = context_.message.MessageContext,
    ) -> context_.message.MessageContext:
        """
        Get the :obj:`~.context.message.MessageContext` instance for the given event.

        Args:
            event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): Event to get the message context
                for.
            command (:obj:`~.commands.message.MessageCommand`): Command that the context is for.
            cls (Type[:obj:`~.context.message.MessageContext`]): Context class to instantiate. Defaults to
                :obj:`~.context.message.MessageContext`.

        Returns:
            :obj:`~.context.message.MessageContext`: Message context instance for the given event.
        """
        return cls(self, event, command)

    async def get_user_context(
        self,
        event: hikari.InteractionCreateEvent,
        command: commands.user.UserCommand,
        cls: t.Type[context_.user.UserContext] = context_.user.UserContext,
    ) -> context_.user.UserContext:
        """
        Get the :obj:`~.context.user.UserContext` instance for the given event.

        Args:
            event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): Event to get the user context for.
            command (:obj:`~.commands.slash.SlashCommand`): Command that the context is for.
            cls (Type[:obj:`~.context.user.UserContext`]): Context class to instantiate. Defaults to
                :obj:`~.context.user.UserContext`.

        Returns:
            :obj:`~.context.user.UserContext`: User context instance for the given event.
        """
        return cls(self, event, command)

    async def get_application_command_context(
        self, event: hikari.InteractionCreateEvent
    ) -> t.Optional[context_.base.ApplicationContext]:
        """
        Get the appropriate subclass instance of :obj:`~.context.base.Application` for the given event.

        Args:
            event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): Event to get the context for.

        Returns:
            :obj:`~.context.base.ApplicationContext`: Context instance for the given event.
        """
        assert isinstance(event.interaction, hikari.CommandInteraction)
        cmd = self._get_application_command(event.interaction)
        if cmd is None:
            return None

        if isinstance(cmd, commands.slash.SlashCommand):
            return await self.get_slash_context(event, cmd)
        elif isinstance(cmd, commands.user.UserCommand):
            return await self.get_user_context(event, cmd)
        elif isinstance(cmd, commands.message.MessageCommand):
            return await self.get_message_context(event, cmd)
        return None

    async def invoke_application_command(self, context: context_.base.ApplicationContext) -> None:
        """
        Invokes the appropriate application command for the given context and handles event
        dispatching for the command invocation.

        Args:
            context (:obj:`~.context.base.ApplicationContext`): Context to invoke application commands under.

        Returns:
            ``None``
        """
        cmd_events = self._get_events_for_application_command(context.command)
        await self.dispatch(cmd_events[0](app=self, command=context.command, context=context))

        try:
            await context.invoke()
        except Exception as exc:
            new_exc = exc
            if not isinstance(exc, errors.LightbulbError):
                new_exc = errors.CommandInvocationError(
                    f"An error occurred during command {context.command.name!r} invocation", original=exc
                )
            assert isinstance(new_exc, errors.LightbulbError)
            error_event = cmd_events[2](app=self, exception=new_exc, context=context)
            handled = await self.maybe_dispatch_error_event(
                error_event,
                [
                    getattr(context.command, "error_handler", None),
                    getattr(context.command.plugin, "_error_handler", None),
                ],
            )

            if not handled:
                raise new_exc
        else:
            await self.dispatch(cmd_events[1](app=self, command=context.command, context=context))

    async def handle_interaction_create_for_application_commands(self, event: hikari.InteractionCreateEvent) -> None:
        """
        Application command :obj:`~hikari.events.interaction_events.InteractionCreateEvent` listener. This handles
        fetching the context, dispatching events, and invoking the appropriate command.

        Args:
            event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): Event that application commands
                will be processed for.

        Returns:
            ``None``
        """
        if not isinstance(event.interaction, hikari.CommandInteraction):
            return

        context = await self.get_application_command_context(event)
        if context is None:
            return

        await self.invoke_application_command(context)

    async def handle_interaction_create_for_autocomplete(self, event: hikari.InteractionCreateEvent) -> None:
        """
        Autocomplete :obj:`~hikari.events.interaction_events.InteractionCreateEvent` listener. This handles resolving
        the function to use for autocompletion, response conversion into :obj:`~hikari.commands.CommandChoice` and
        responding to the interaction with the provided options.

        Args:
            event (:obj:`~hikari.events.interaction_events.InteractionCreateEvent`): Event that autocomplete
                will be processed for.

        Returns:
            ``None``
        """
        if not isinstance(event.interaction, hikari.AutocompleteInteraction):
            return

        assert event.interaction.command_type is hikari.CommandType.SLASH
        assert event.interaction.options is not None and len(event.interaction.options) > 0

        def is_focused(opt: hikari.AutocompleteInteractionOption) -> bool:
            return opt.is_focused

        def get_focused(opts: t.Sequence[hikari.AutocompleteInteractionOption]) -> hikari.AutocompleteInteractionOption:
            return next(filter(is_focused, opts), opts[0])

        def flatten_command_option(
            opt: hikari.AutocompleteInteractionOption,
        ) -> t.Tuple[hikari.AutocompleteInteractionOption, t.Sequence[str]]:
            current = opt
            name = [current.name]

            while current.type in (hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP):
                assert current.options is not None
                current = get_focused(current.options)
                name.append(current.name)

            return current, name

        option, full_name = flatten_command_option(get_focused(event.interaction.options))

        cmd = self.get_slash_command(event.interaction.command_name)
        if cmd is None:
            return

        for part in full_name[:-1]:
            if not isinstance(cmd, commands.slash.SlashGroupMixin):
                return

            cmd = cmd.get_subcommand(part)
            if cmd is None:
                return

        callback = cmd._initialiser._autocomplete_callbacks.get(full_name[-1])
        if callback is None:
            return

        # Invoke the autocomplete callback
        response = await callback(option, event.interaction)
        if not response:
            await event.interaction.create_response([])
            return

        def convert_response_value(
            val: t.Union[str, int, float, hikari.api.AutocompleteChoiceBuilder],
        ) -> hikari.api.AutocompleteChoiceBuilder:
            if isinstance(val, (str, int, float)):
                return hikari.impl.AutocompleteChoiceBuilder(name=str(val), value=val)

            return val

        resp_to_send: t.List[hikari.api.AutocompleteChoiceBuilder] = []
        if isinstance(response, (str, int, float, hikari.api.AutocompleteChoiceBuilder)):
            resp_to_send.append(convert_response_value(response))
        elif isinstance(response, collections.abc.Sequence):
            for item in response:
                resp_to_send.append(convert_response_value(item))
        else:
            _LOGGER.error("Invalid response returned from autocomplete handler %r", callback.__name__)  # type: ignore[unreachable]

        try:
            await event.interaction.create_response(resp_to_send)
        except hikari.NotFoundError as e:
            _LOGGER.debug("Failed sending autocomplete response", exc_info=(type(e), e, e.__traceback__))
