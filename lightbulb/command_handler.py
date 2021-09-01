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

__all__: typing.Final[typing.List[str]] = ["Bot", "when_mentioned_or"]

import asyncio
import collections
import functools
import importlib
import inspect
import logging
import re
import sys
import typing

import hikari
from hikari.internal import ux
from multidict import CIMultiDict

from lightbulb import commands
from lightbulb import context as context_
from lightbulb import errors
from lightbulb import events
from lightbulb import help as help_
from lightbulb import plugins
from lightbulb import slash_commands
from lightbulb.converters import _DefaultingConverter
from lightbulb.converters import _GreedyConverter
from lightbulb.slash_commands.commands import _serialise_command
from lightbulb.utils import maybe_await

_LOGGER = logging.getLogger("lightbulb")

# XXX: can't we use `str.split()` here, which splits on all whitespace in the same way?
ARG_SEP_REGEX = re.compile(r"(?:\s+|\n)")


def when_mentioned_or(prefix_provider):
    """
    Helper function which allows the bot's mentions to be used as the command prefix, as well
    as any other prefix(es) passed in or supplied by the ``prefix_provider``.

    Args:
        prefix_provider: An object that is a prefix, contains prefixes, or returns prefixes.

    Example:

        .. code-block:: python

            # The below are all valid
            bot = lightbulb.Bot(prefix=lightbulb.when_mentioned_or("!"), ...)

            bot = lightbulb.Bot(prefix=lightbulb.when_mentioned_or(["!", "?"]), ...)

            # Using only mentions as the prefix
            bot = lightbulb.Bot(prefix=lightbulb.when_mentioned_or(None), ...)

            # Using with a get_prefix function
            def get_prefix(bot, message):
                # Do something to get the prefixes
                return prefixes

            bot = lightbulb.Bot(prefix=lightbulb.when_mentioned_or(get_prefix), ...)
    """

    async def get_prefixes(bot, message):
        mentions = [f"<@{bot.get_me().id}> ", f"<@!{bot.get_me().id}> "]

        if callable(prefix_provider):
            prefixes = prefix_provider(bot, message)
            if inspect.iscoroutine(prefixes) or isinstance(prefixes, asyncio.Future):
                prefixes = await prefixes
        else:
            prefixes = prefix_provider

        if isinstance(prefixes, str):
            return mentions + [prefixes]
        elif isinstance(prefixes, typing.Iterable):
            return mentions + list(prefixes)
        elif prefixes is None:
            return mentions
        else:
            return mentions + [prefix async for prefix in prefixes]

    return get_prefixes


# Prefixes may be a string or iterable of strings. A string is a sequence of strings too by definition,
# so this type hint _is_ correct.
def _return_prefix(_: typing.Any, __: typing.Any, *, prefixes: typing.Iterable[str]) -> typing.Sequence[str]:
    return prefixes


class Bot(hikari.GatewayBot):
    """
    A subclassed implementation of :class:`hikari.impl.bot.BotAppImpl` which contains a command handler.
    This should be instantiated instead of the superclass if you want to be able to use
    the command handler implementation provided.

    The prefix argument will accept any of the following:

    - A single string, eg ``'!'``

    - An iterable (such as a list) of strings, eg ``['!', '?']``

    - A function or coroutine that takes **only** two arguments, ``bot`` and ``message``, and that returns a single string or iterable of strings.

    Args:
        prefix: The bot's command prefix, iterable of prefixes, or callable that returns
            a prefix or iterable of prefixes.
        insensitive_commands (:obj:`bool`): Whether or not commands should be case-insensitive or not.
            Defaults to False (commands are case-sensitive).
        ignore_bots (:obj:`bool`): Ignore other bot's messages invoking your bot's commands if True (default), else not.
            invoked by other bots. Defaults to ``True``.
        owner_ids (List[ :obj:`int` ]): IDs that the bot should treat as owning the bot.
        help_class (:obj:`~.help.HelpCommand`): The **uninstantiated** class the bot should use for it's help command.
            Defaults to :obj:`~.help.HelpCommand`. Any class passed should always be this class or subclass of
            this class.
        delete_unbound_slash_commands (:obj:`bool`): Whether or not to delete unbound slash commands when the
            bot starts. This will remove any slash commands that do not have a
            :obj:`~lightbulb.slash_commands.SlashCommand` object bound to them when the bot starts but are registered
            according to  discord's API. Defaults to ``True``.
        recreate_changed_slash_commands (:obj:`bool`): Whether or not to send the new version of the slash command
            to discord if the bot detects that the version on discord does not match the local version. Defaults
            to ``True``.
        slash_commands_only (:obj:`bool`): Whether or not the bot will only be using slash commands to interact
            with discord. Defaults to ``False``. If this is ``False`` and no prefix is provided then an error will
            be raised. If ``True``, then you do not need to provide a prefix.
        **kwargs: Other parameters passed to the :class:`hikari.impl.bot.BotAppImpl` constructor.
    """

    def __init__(
        self,
        *,
        prefix=None,
        insensitive_commands: bool = False,
        ignore_bots: bool = True,
        owner_ids: typing.Iterable[int] = (),
        help_class: typing.Type[help_.HelpCommand] = help_.HelpCommand,
        delete_unbound_slash_commands: bool = True,
        recreate_changed_slash_commands: bool = True,
        slash_commands_only: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        if prefix is None and slash_commands_only is False:
            raise TypeError("slash_commands_only is False but no prefix was provided.")

        if not slash_commands_only:
            self.subscribe(hikari.MessageCreateEvent, self.handle)
        self.subscribe(hikari.InteractionCreateEvent, self.handle_slash_commands)
        self.subscribe(hikari.StartingEvent, self._manage_slash_commands)

        if isinstance(prefix, str):
            self.get_prefix = functools.partial(_return_prefix, prefixes=[prefix])
        elif isinstance(prefix, collections.abc.Iterable):
            self.get_prefix = functools.partial(_return_prefix, prefixes=prefix)
        else:
            self.get_prefix = prefix

        self.ignore_bots: bool = ignore_bots
        self.owner_ids: typing.Iterable[int] = owner_ids
        """Iterable of the bot's owner IDs. This can be set by :meth:`Bot.fetch_owner_ids` if not given in the constructor."""
        self.insensitive_commands = insensitive_commands
        self.extensions: typing.List[str] = []
        """A list of extensions currently loaded to the bot."""
        self.plugins: typing.MutableMapping[str, plugins.Plugin] = {}
        """A mapping of plugin name to plugin object currently added to the bot."""
        self._commands: typing.MutableMapping[str, commands.Command] = (
            dict() if not self.insensitive_commands else CIMultiDict()
        )
        self.commands: typing.Set[commands.Command] = set()
        """A set containing all commands and groups registered to the bot."""
        self._checks = []

        self._delete_unbound_slash_commands = delete_unbound_slash_commands
        self._recreate_changed_slash_commands = recreate_changed_slash_commands
        self._slash_commands: typing.MutableMapping[str, slash_commands.TopLevelSlashCommandBase] = {}
        self.slash_commands: typing.Set[slash_commands.TopLevelSlashCommandBase] = set()
        """A set containing all slash commands registered to the bot."""

        self._app: typing.Optional[hikari.PartialApplication] = None

        self._help_impl = help_class(self)

    @staticmethod
    def print_banner(banner: typing.Optional[str], allow_color: bool, force_color: bool) -> None:
        ux.print_banner(banner, allow_color, force_color)
        if banner == "hikari":
            sys.stdout.write(f"Thank you for using lightbulb!\n")

    @property
    def help_command(self):
        """The instance of the help class used by the bot."""
        return self._help_impl

    @help_command.setter
    def help_command(self, new_help_instance: help_.HelpCommand):
        self._help_impl = new_help_instance

    async def fetch_owner_ids(self) -> None:
        """
        Fetches the IDs of the bot's owner(s) from the API and stores them in
        :attr:`~.command_handler.Bot.owner_ids`

        Returns:
            ``None``
        """
        # TODO - add way to flush the owner_id cache
        application = await self.rest.fetch_application()
        self.owner_ids = []
        if application.owner is not None:
            self.owner_ids.append(application.owner.id)
        if application.team is not None:
            self.owner_ids.extend([member_id for member_id in application.team.members])

    def command(self, **kwargs) -> typing.Callable:
        """
        A decorator that registers a coroutine as a command for the handler.

        Keyword Args:
            **kwargs: See :obj:`~.commands.command` for valid kwargs.

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(...)

                @bot.command()
                async def ping(ctx):
                    await ctx.respond("Pong!")

        See Also:
            :meth:`~.command_handler.Bot.add_command`
        """

        def decorate(func: typing.Callable):
            return self.add_command(func, **kwargs)

        return decorate

    def group(self, **kwargs) -> typing.Callable:
        """
        A decorator that registers a coroutine as a command group for the handler.

        Keyword Args:
            **kwargs: See :obj:`~.commands.group` for valid kwargs.

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(...)

                @bot.group()
                async def foo(ctx):
                    await ctx.respond("Bar")

        See Also:
            :meth:`~.commands.Group.command` for how to add subcommands to a group.
        """

        def decorate(func: typing.Callable):
            return self.add_group(func, **kwargs)

        return decorate

    def check(self):
        """
        A decorator that registers a coroutine as a global check.

        This check coroutine will be called before any command invocation.

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(...)

                @bot.check()
                async def global_guild_only(ctx):
                    return ctx.guild_id is not None

        See Also:
            :meth:`~.command_handler.Bot.add_check`
        """

        def decorate(func) -> None:
            self.add_check(func)

        return decorate

    def add_command(self, func: typing.Union[typing.Callable, commands.Command], **kwargs) -> commands.Command:
        """
        Adds a command to the bot. Similar to the ``command`` decorator.

        Args:
            func (:obj:`typing.Callable`): The function or command object to register as a command.

        Keyword Args:
            **kwargs: See :obj:`~.commands.command` for valid kwargs.

        Returns:
            :obj:`~.commands.Command`: Command added to the bot.

        Raises:
            :obj:`NameError`: If the name or an alias of the command being added conflicts with
                an existing command.

        Example:

            .. code-block:: python

                import lightbulb

                bot = lightbulb.Bot(...)

                async def ping(ctx):
                    await ctx.respond("Pong!")

                bot.add_command(ping)

        See Also:
            :meth:`~.command_handler.Bot.command`
        """
        if not isinstance(func, commands.Command):
            name = kwargs.get("name", func.__name__)
            cls = kwargs.get("cls", commands.Command)
            func = cls(
                func,
                name,
                kwargs.get("allow_extra_arguments", True),
                kwargs.get("aliases", []),
                kwargs.get("hidden", False),
            )

        if self.insensitive_commands:
            if set([name.casefold() for name in self._commands.keys()]).intersection(
                {func.name.casefold(), *[a.casefold() for a in func._aliases]}
            ):
                raise NameError(f"Command {func.name!r} has name or alias already registered.")
        else:
            if set(self._commands.keys()).intersection({func.name, *func._aliases}):
                raise NameError(f"Command {func.name!r} has name or alias already registered.")

        self.commands.add(func)
        self._commands[func.name] = func
        for alias in func._aliases:
            self._commands[alias] = func
        _LOGGER.debug("new command registered %r", func.name)
        return self._commands[func.name]

    def add_group(self, func: typing.Union[typing.Callable, commands.Group], **kwargs) -> commands.Group:
        """
        Adds a command group to the bot. Similar to the ``group`` decorator.

        Args:
            func (Union[ :obj:`typing.Callable`, :obj:`~.commands.Group` ]): The function or group object
                to register as a command group.

        Keyword Args:
            **kwargs: See :obj:`~.commands.group` for valid kwargs.

        Returns:
            :obj:`~.commands.Group`: Group added to the bot.

        Raises:
            :obj:`AttributeError`: If the name or an alias of the group being added conflicts with
                an existing command.

        See Also:
            :meth:`~.command_handler.Bot.group`
            :meth:`~.command_handler.Bot.add_command`
        """
        if not isinstance(func, commands.Group):
            name = kwargs.get("name", func.__name__)
            cls = kwargs.get("cls", commands.Group)
            func = cls(
                func,
                name,
                kwargs.get("allow_extra_arguments", True),
                kwargs.get("aliases", []),
                kwargs.get("hidden", False),
                insensitive_commands=kwargs.get("insensitive_commands", False),
            )

        if set(self._commands.keys()).intersection({func.name, *func._aliases}):
            raise AttributeError(f"Command {func.name!r} has name or alias already registered.")

        self.commands.add(func)
        self._commands[func.name] = func
        for alias in func._aliases:
            self._commands[alias] = func
        _LOGGER.debug("new group registered %r", func.name)
        return self._commands[func.name]

    def add_check(self, func: typing.Callable[[context_.Context], typing.Coroutine[None, None, bool]]) -> None:
        """
        Add a coroutine as a global check for the bot.

        This coroutine will be called before any command invocation.

        Args:
            func (Callable[[ :obj:`~.context.Context ], Coroutine[ ``None``, ``None``, :obj:`bool` ]]): The
                coroutine to add as a global check.

        Returns:
            ``None``
        """
        self._checks.append(func)

    def add_plugin(self, plugin: typing.Union[plugins.Plugin, typing.Type[plugins.Plugin]]) -> None:
        """
        Add a :obj:`~.plugins.Plugin` instance or class to the bot, including all of the plugin commands.

        If a class is passed in instead of a plugin instance, then the bot will attempt to instantiate it and
        then add the newly-created plugin instance to the bot.

        Args:
            plugin (Union[:obj:`~.plugins.Plugin`, Type[:obj:`~.plugins.Plugin`]]): Plugin instance or plugin
                subclass to add to the bot.

        Returns:
            ``None``

        Raises:
            :obj:`NameError`: If the name of the plugin being added conflicts with an
                existing plugin.
        """
        if inspect.isclass(plugin) and issubclass(plugin, plugins.Plugin):
            return self.add_plugin(plugin())

        if plugin.name in self.plugins:
            raise NameError(f"A plugin named {plugin.name!r} is already registered.")

        self.plugins[plugin.name] = plugin
        for command in plugin._commands.values():
            if isinstance(command, commands.Group):
                self.add_group(command)
            else:
                self.add_command(command)

        for event_type, listeners in plugin.listeners.items():
            for listener in listeners:
                callback = listener.__get__(plugin, type(plugin))
                self.subscribe(listener.event_type, callback)
                _LOGGER.debug("new listener registered %r (%s)", callback.__name__, listener.event_type.__name__)

        _LOGGER.debug("new plugin registered %r", plugin.name)

    def get_command(self, name: str) -> typing.Optional[commands.Command]:
        """
        Get a command object from its registered name.

        Args:
            name (:obj:`str`): The name of the command to get the object for.

        Returns:
            Optional[ :obj:`~.commands.Command` ]: Command object registered to that name.
        """
        tokens = name.split()
        this = self._commands.get(tokens.pop(0))

        if not tokens:
            return this
        if this is None:
            return this

        for token in tokens:
            this = this.get_subcommand(token)

        return this

    def get_plugin(self, name: str) -> typing.Optional[plugins.Plugin]:
        """
        Get a plugin object from its registered name.

        Args:
             name (:obj:`str`): The name of the plugin to get the object for.

        Returns:
            Optional[ :obj:`~.commands.Command` ]: Plugin object registered to that name.
        """
        return self.plugins.get(name)

    def remove_command(self, name: str) -> typing.Optional[str]:
        """
        Remove a command from the bot and return its name or ``None`` if no command was removed.

        Args:
            name (:obj:`str`): The name of the command to remove.

        Returns:
            Optional[ :obj:`str` ]: Name of the command that was removed.
        """
        command = self._commands.pop(name, None)

        if command is None:
            return None

        self.commands.remove(command)

        keys_to_remove = [command.name, *command._aliases]
        keys_to_remove.remove(name)
        for key in keys_to_remove:
            self._commands.pop(key)
        _LOGGER.debug("command removed %r", command.name)

        return command.name

    def remove_plugin(self, name: str) -> typing.Optional[str]:
        """
        Remove a plugin from the bot and return its name or ``None`` if no plugin was removed.

        Args:
            name (:obj:`str`): The name of the plugin to remove.

        Returns:
            Optional[ :obj:`str` ]: Name of the plugin that was removed.
        """
        plugin = self.plugins.pop(name, None)

        if plugin is None:
            return None

        plugin.plugin_remove()

        for k in plugin._commands.keys():
            self.remove_command(k)

        for event_type, listeners in plugin.listeners.items():
            for listener in listeners:
                callback = listener.__get__(plugin, type(plugin))
                self.unsubscribe(listener.event_type, callback)
                _LOGGER.debug("listener removed %r (%s)", callback.__name__, listener.event_type.__name__)

        _LOGGER.debug("plugin removed %r", plugin.name)

        return plugin.name

    def load_extension(self, extension: str) -> None:
        """
        Load an external extension into the bot. Extension name follows the format ``<directory>.<filename>``
        The extension **must** contain a function ``load`` which takes a single argument which will be the
        bot instance you are loading the extension into.

        Args:
            extension (:obj:`str`): The name of the extension to load.

        Returns:
            ``None``

        Raises:
            :obj:`~.errors.ExtensionAlreadyLoaded`: If the extension has already been loaded.
            :obj:`~.errors.ExtensionMissingLoad`: If the extension to be loaded does not contain a ``load`` function.

        Example:
            This method is useful when wanting to split your bot up into multiple files.
            An example extension is seen below  - ``example.py`` and would be loaded by calling
            the following: ``bot.load_extension("example")``

            .. code-block:: python

                import lightbulb

                class MyPlugin(lightbulb.Plugin):
                    ...

                def load(bot):
                    bot.add_plugin(MyPlugin())
        """
        if extension in self.extensions:
            raise errors.ExtensionAlreadyLoaded(text=f"Extension {extension!r} is already loaded.")

        module = importlib.import_module(extension)

        if not hasattr(module, "load"):
            raise errors.ExtensionMissingLoad(text=f"Extension {extension!r} is missing a load function")
        else:
            module.load(self)
            self.extensions.append(extension)
            _LOGGER.debug("new extension loaded %r", extension)

    def unload_extension(self, extension: str) -> None:
        """
        Unload an external extension from the bot. This method relies on a function, ``unload``
        existing in the extension which the bot will use to remove all commands and/or plugins
        from the bot.

        Args:
            extension (:obj:`str`): The name of the extension to unload.

        Returns:
            ``None``

        Raises:
            :obj:`~.errors.ExtensionNotLoaded`: If the extension has not been loaded.
            :obj:`~.errors.ExtensionMissingUnload`: If the extension does not contain an ``unload`` function.

        Example:

            .. code-block:: python

                import lightbulb

                class MyPlugin(lightbulb.Plugin):
                    ...

                def load(bot):
                    bot.add_plugin(MyPlugin())

                def unload(bot):
                    bot.remove_plugin("MyPlugin")
        """
        if extension not in self.extensions:
            raise errors.ExtensionNotLoaded(text=f"Extension {extension!r} is not loaded.")

        module = importlib.import_module(extension)

        if not hasattr(module, "unload"):
            raise errors.ExtensionMissingUnload(text=f"Extension {extension!r} is missing an unload function")
        else:
            module.unload(self)
            self.extensions.remove(extension)
            del sys.modules[extension]
            _LOGGER.debug("extension unloaded %r", extension)

    def reload_extension(self, extension: str) -> None:
        """
        Reload a bot extension. This method is atomic and so the bot will
        revert to the previous loaded state if the extension encounters a problem
        during unloading or loading.

        Args:
            extension (:obj:`str`): The name of the extension to be reloaded.

        Returns:
            ``None``
        """
        _LOGGER.debug("reloading extension %r", extension)
        old = sys.modules[extension]
        try:
            self.unload_extension(extension)
            self.load_extension(extension)
        except Exception as e:
            sys.modules[extension] = old
            self.load_extension(extension)
            raise e
        else:
            del old

    def walk_commands(self) -> typing.Generator[commands.Command, None, None]:
        """
        A generator that walks through all commands and subcommands registered to the bot.

        Yields:
            :obj:`~.commands.Command`: All commands, groups and subcommands registered to the bot.
        """
        for command in self.commands:
            yield command
            if isinstance(command, commands.Group):
                yield from command.walk_commands()

    async def send_help(
        self, context: context_.Context, obj: typing.Union[commands.Command, plugins.Plugin] = None
    ) -> None:
        """
        Send help to the provided context to the specified object, or send the bot's help overview if
        no object to send help for is supplied.

        Args:
            context (:obj:`~.context.Context`): The context to send help to.
            obj (Union[ :obj:`~.commands.Command`, :obj:`~.plugins.Plugin` ]): The object to send help for.
                Defaults to ``None``.

        Returns:
            ``None``
        """
        if obj is None:
            await self.help_command.send_help_overview(context)
        elif isinstance(obj, commands.Group):
            await self.help_command.send_group_help(context, obj)
        elif isinstance(obj, commands.Command):
            await self.help_command.send_command_help(context, obj)
        elif isinstance(obj, plugins.Plugin):
            await self.help_command.send_plugin_help(context, obj)

    def get_context(
        self, message: hikari.Message, prefix: str, invoked_with: str, invoked_command: commands.Command
    ) -> context_.Context:
        """
        Get the :obj:`~.context.Context` instance for the given arguments. This should be overridden
        if you wish to supply a custom :obj:`~.context.Context` class to your commands.

        Args:
            message (:obj:`hikari.Message`): The message the context is for.
            prefix (:obj:`str`): The prefix used in this context.
            invoked_with (:obj:`str`): The command name/alias used to trigger invocation.
            invoked_command (:obj:`~.commands.Command`): The command that will be invoked.

        Returns:
            :obj:`~.context.Context`: The context to be used for the command invocation.
        """
        return context_.Context(self, message, prefix, invoked_with, invoked_command)

    async def _evaluate_checks(self, command: commands.Command, context: context_.Context) -> bool:
        checks = [*self._checks, *command.checks]
        if command.plugin is not None:
            checks.append(command.plugin.plugin_check)

        failed_checks = []
        for check in checks:
            try:
                if not await check(context):
                    failed_checks.append(
                        errors.CheckFailure(f"Check {check.__name__} failed for command {command.name}")
                    )
            except Exception as ex:
                error = errors.CheckFailure(str(ex))
                error.__cause__ = ex
                failed_checks.append(ex)

        if len(failed_checks) > 1:
            raise errors.CheckFailure("Multiple checks failed: " + ", ".join(str(ex) for ex in failed_checks))
        elif failed_checks:
            raise failed_checks[0]
        return True

    async def _dispatch_command_error_event_from_exception(
        self,
        exception: errors.CommandError,
        message: hikari.Message,
        context: typing.Optional[context_.Context] = None,
        command: typing.Optional[commands.Command] = None,
    ) -> None:
        error_event = events.CommandErrorEvent(
            app=self, exception=exception, message=message, context=context, command=command
        )

        handled = False
        if command is not None:
            if command._error_listener is not None:
                handled = bool(await command._error_listener(error_event))
            if not handled and self.get_listeners(events.CommandErrorEvent, polymorphic=True):
                await self.dispatch(error_event)
                handled = True
        else:
            if self.get_listeners(events.CommandErrorEvent, polymorphic=True):
                await self.dispatch(error_event)
                handled = True

        if not handled:
            raise exception

    async def _resolve_prefix(self, message: hikari.Message) -> typing.Optional[str]:
        prefixes = await maybe_await(self.get_prefix, self, message)

        if isinstance(prefixes, str):
            prefixes = [prefixes]

        prefixes.sort(key=len, reverse=True)

        for prefix in prefixes:
            if message.content.startswith(prefix):
                return prefix
        return None

    def _validate_command_exists(self, invoked_with) -> commands.Command:
        if (command := self.get_command(invoked_with)) is not None:
            return command
        raise errors.CommandNotFound(invoked_with)

    async def resolve_args_for_command(
        self, context: context_.Context, command: commands.Command, raw_arg_string: str
    ) -> typing.Tuple[typing.List[str], typing.Dict[str, str]]:
        """
        Resolve the appropriate command arguments from an unparsed string
        containing the raw command arguments and attempt to convert them into
        the appropriate types given the type hint.

        This method can be overridden if you wish to customise how arguments
        are parsed and converted for all the commands. If you override this then it is important
        that it at least returns a tuple containing an empty list if no positional arguments
        were resolved, and an empty dict if no keyword arguments were resolved.

        If you override this method then you may find the :obj:`~.stringview.StringView`
        class useful for extracting the arguments from the raw string and the property
        :obj:`~.command.arg_details` which contains information about the command's arguments
        and which are optional or required.

        Args:
            context (:obj:`~.context.Context`): The invocation context for the command.
            command (:obj:`~.commands.Command`): The command to resolve the arguments for.
            raw_arg_string (:obj:`str`): String containing the raw, unparsed arguments.

        Returns:
            Tuple[ List[ :obj:`str` ], Dict[ :obj:`str1, :obj:`str` ] ]: Positional and keyword
                arguments the command should be invoked with.

        Raises:
            :obj:`~.errors.TooManyArguments`: The command does not ignore extra arguments and too many
                arguments were supplied by the user.
            :obj:`~.errors.NotEnoughArguments`: Not enough arguments were provided by the user to fill
                all required argument fields.
            :obj:`~.errors.ConverterFailure`: Argument value conversion failed.
        """
        converters = command.arg_details.converters[:]
        arg_names = command.arg_details.arguments[:]
        args, kwargs = [], {}

        arg_string = raw_arg_string
        while converters:
            conv = converters.pop(0)
            arg_name = arg_names.pop(0)

            if not isinstance(conv, (_DefaultingConverter, _GreedyConverter)) and not arg_string:
                raise errors.NotEnoughArguments(command, [arg_name, *arg_names])

            try:
                conv_out, arg_string = await conv.convert(context, arg_string)
            except (ValueError, TypeError, errors.ConverterFailure):
                raise errors.ConverterFailure(f"Converting failed for argument {arg_name!r}")

            if isinstance(conv_out, dict):
                kwargs.update(conv_out)
            elif isinstance(conv, _GreedyConverter) and conv.unpack:
                args.extend(conv_out)
            else:
                args.append(conv_out)

        if arg_string and not command._allow_extra_arguments:
            raise errors.TooManyArguments(command)

        return args, kwargs

    async def _invoke_command(
        self,
        command: commands.Command,
        context: context_.Context,
        args: typing.Sequence[str],
        kwargs: typing.Mapping[str, str],
    ) -> None:
        await command.invoke(context, *args, **kwargs)

    async def process_commands_for_event(self, event: hikari.MessageCreateEvent) -> None:
        """
        Carries out all command and argument parsing, evaluates checks and ultimately invokes
        a command if the event passed is deemed to contain a command invocation.

        It is not recommended that you override this method - if you do you should make sure that
        you know what you are doing.

        Args:
            event (:obj:`hikari.MessageCreateEvent`): The event to process commands for.

        Returns:
            ``None``
        """
        prefix = await self._resolve_prefix(event.message)
        if prefix is None:
            return

        new_content = event.message.content[len(prefix) :]

        if not new_content or new_content.isspace():
            return

        split_args = ARG_SEP_REGEX.split(new_content, maxsplit=1)
        invoked_with, command_args = split_args[0], "".join(split_args[1:])

        if not invoked_with:
            # Return if the character immediately following the command prefix
            # is whitespace to prevent IndexError later on
            return

        try:
            command = self._validate_command_exists(invoked_with)
        except errors.CommandNotFound as ex:
            await self._dispatch_command_error_event_from_exception(ex, event.message)
            return

        temp_args = command_args
        final_args = command_args
        while isinstance(command, commands.Group) and command_args:
            next_split = ARG_SEP_REGEX.split(temp_args, maxsplit=1)
            next_arg, temp_args = next_split[0], "".join(next_split[1:])
            prev_command = command
            maybe_subcommand = command.get_subcommand(next_arg)

            if maybe_subcommand is None:
                command = prev_command
                break
            else:
                command = maybe_subcommand
                final_args = temp_args

        context = self.get_context(event.message, prefix, invoked_with, command)

        await self.dispatch(events.CommandInvocationEvent(app=self, command=command, context=context))
        if (before_invoke := command._before_invoke) is not None:
            await before_invoke(context)

        try:
            positional_args, keyword_arg = await self.resolve_args_for_command(context, command, final_args)
            if not await maybe_await(command._check_exempt_predicate, context):
                await self._evaluate_checks(command, context)
            else:
                _LOGGER.debug("checks bypassed for command %r", context.message.content)
        except (
            errors.NotEnoughArguments,
            errors.TooManyArguments,
            errors.CheckFailure,
            errors.CommandSyntaxError,
            errors.ConverterFailure,
        ) as ex:
            await self._dispatch_command_error_event_from_exception(ex, event.message, context, command)
            return

        try:
            await self._invoke_command(command, context, positional_args, keyword_arg)
        except errors.CommandError as ex:
            await self._dispatch_command_error_event_from_exception(ex, event.message, context, command)
            return
        except Exception as ex:
            new_ex = errors.CommandInvocationError(f"{type(ex).__name__}: {ex}", ex)
            await self._dispatch_command_error_event_from_exception(new_ex, event.message, context, command)
            return

        if (after_invoke := command._after_invoke) is not None:
            await after_invoke(context)

        await self.dispatch(events.CommandCompletionEvent(app=self, command=command, context=context))

    async def handle(self, event: hikari.MessageCreateEvent) -> None:
        """
        The message listener that deals with validating the invocation messages. If invocation message
        is valid then it will delegate parsing and invocation to :obj:`Bot.process_commands_for_event`.

        You can override this method to customise how the bot should validate that a message could
        contain a command invocation, for example making it ignore specific guilds or users.

        If you choose to override this method, it should await :obj:`Bot.process_commands_for_event`
        otherwise no commands will ever be invoked.

        Args:
            event (:obj:`hikari.events.message.MessageCreateEvent`): The message create event containing
                a possible command invocation.

        Returns:
            ``None``
        """
        if self.ignore_bots and not event.is_human:
            return

        if not event.message.content:
            return

        await self.process_commands_for_event(event)

    def add_slash_command(
        self, command: typing.Type[slash_commands.TopLevelSlashCommandBase], create: bool = False
    ) -> None:
        """
        Registers a slash command with the bot.

        Args:
            command (Type[:obj:`~lightbulb.slash_commands.SlashCommandBase`]): The slash command class to register
                to the bot. This should **not** be instantiated.
            create (:obj:`bool`): Whether or not to send a create request to discord when the command is added.
                Defaults to ``False``.

        Returns:
            ``None``

        Warning:
            The ``create`` argument **must** be ``False`` if the command is being added to the bot before
            the bot has started (i.e. ``bot.run()`` has not yet been called).
        """
        cmd = command(self)

        if cmd.name in self._slash_commands:
            raise NameError(f"Slash command {cmd.name!r} has a name already registered.")

        self._slash_commands[cmd.name] = cmd
        self.slash_commands.add(cmd)

        if create and self._app is not None:
            _LOGGER.debug("creating slash command %r", cmd.name)
            asyncio.create_task(cmd.auto_create(self._app))
        elif create and self._app is None:
            _LOGGER.debug("not adding slash command %r as the bot has not started", cmd.name)

        _LOGGER.debug("slash command added %r", cmd.name)

    def remove_slash_command(self, name: str, delete: bool = False) -> typing.Optional[str]:
        """
        Remove a slash command from the bot and return its name or ``None`` if no command was removed.

        Args:
            name (:obj:`str`): The name of the slash command to remove.
            delete (:obj:`bool`): Whether or not to delete the command from discord when it is removed. Defaults
                to ``False``.

        Returns:
            Optional[ :obj:`str` ]: Name of the slash command that was removed.
        """
        name = name.lower()

        cmd = self._slash_commands.pop(name)
        if cmd is not None:
            self.slash_commands.remove(cmd)

            if delete and self._app is not None:
                _LOGGER.debug("purging slash command %r", cmd.name)
                asyncio.create_task(cmd.auto_delete(self._app))
            elif delete and self._app is None:
                _LOGGER.debug("not purging slash command %r as the bot has not started", cmd.name)

            _LOGGER.debug("slash command removed %r", cmd.name)

        return cmd.name if cmd is not None else None

    def get_slash_command(self, name: str) -> typing.Optional[slash_commands.TopLevelSlashCommandBase]:
        """
        Gets the slash command with the given name, or ``None`` if one with that name does
        not exist.

        Args:
            name (:obj:`str`): The name of the slash command to get the object for.

        Returns:
            Optional[:obj:`~lightbulb.slash_commands.TopLevelSlashCommandBase`]: Retrieved slash command or ``None``
                if not found.
        """
        return self._slash_commands.get(name)

    async def purge_slash_commands(self, *guild_ids: hikari.Snowflakeish, global_commands: bool = False) -> None:
        """
        Purges all slash commands from the guilds with the specified IDs, and all the global slash
        commands if ``global_commands`` is ``True``. Useful if you want to teardown old slash commands from
        the bot and cannot be bothered to fetch them individually yourself. If neither `guild_ids` nor `global_commands`
        is specified then this method will do nothing.

        Args:
            *guild_ids (:obj:`hikari.Snowflakeish`): IDs for the guilds to purge slash commands from.

        Keyword Args:
            global_commands (:obj:`bool`): Whether or not to purge global slash commands from the bot.

        Returns:
            ``None``
        """
        commands_to_remove = []
        if global_commands:
            commands_to_remove.extend(await self.rest.fetch_application_commands(self._app))
        if guild_ids:
            for guild_id in guild_ids:
                commands_to_remove.extend(await self.rest.fetch_application_commands(self._app, guild_id))

        for command in commands_to_remove:
            if command.guild_id is None:
                _LOGGER.debug("deleting global slash command %r", command.name)
            else:
                _LOGGER.debug("deleting slash command %r from guild %r", command.name, str(command.guild_id))
            await command.delete()

    async def handle_slash_commands(self, event: hikari.InteractionCreateEvent) -> None:
        """
        The InteractionCreateEvent listener that handles slash command invocations and
        resolves and invokes the correct callback from the event payload.

        Args:
            event (:obj:`hikari.InteractionCreateEvent`): The InteractionCreateEvent for the slash command
                invocation.
        Returns:
            ``None``
        """
        if not isinstance(event.interaction, hikari.CommandInteraction):
            return

        command = self.get_slash_command(event.interaction.command_name)
        if command is None:
            return

        context = slash_commands.SlashCommandContext(self, event.interaction, command)
        _LOGGER.debug("invoking slash command %r", command.name)
        await command(context)

    async def _manage_slash_commands(self, _):
        self._app = await self.rest.fetch_application()

        global_slash_commands = {c.name: c for c in await self.rest.fetch_application_commands(self._app)}

        guilds = set()
        for cmd in self._slash_commands.values():
            if cmd.enabled_guilds is not None:
                guilds.update(cmd.enabled_guilds)

        _guild_slash_commands = {
            g_id: {c.name: c for c in await self.rest.fetch_application_commands(self._app, g_id)} for g_id in guilds
        }
        guild_slash_commands = collections.defaultdict(list)
        for g_id, cmd_info in _guild_slash_commands.items():
            for cmd in cmd_info.values():
                guild_slash_commands[cmd.name].append([cmd, g_id])

        # Note that the purge_slash_commands method is not used here as the bot only purges
        # commands that appear not to have an implementation registered, as opposed to just
        # purging every command.
        remaining_globals = {} if self._delete_unbound_slash_commands is True else global_slash_commands
        if self._delete_unbound_slash_commands:
            _LOGGER.debug("purging unbound slash commands")
            for cmd in global_slash_commands.values():
                # if an implementation of the slash command is not found
                if self._slash_commands.get(cmd.name) is None:
                    _LOGGER.debug("deleting global slash command %r", cmd.name)
                    await cmd.delete()
                # if our implementation of the slash command is specific to guilds
                elif self._slash_commands[cmd.name].enabled_guilds is not None:
                    _LOGGER.debug("deleting global slash command %r", cmd.name)
                    await cmd.delete()
                else:
                    remaining_globals[cmd.name] = cmd

        remaining_guild_cmds = {}
        if self._delete_unbound_slash_commands:
            for cmd_name, cmds in guild_slash_commands.items():
                for cmd, guild_id in cmds:
                    # if an implementation of the slash command is not found
                    if self._slash_commands.get(cmd.name) is None:
                        _LOGGER.debug("deleting slash command %r from guild %r", cmd.name, str(cmd.guild_id))
                        await cmd.delete()
                    # if our implementation of the slash command doesn't contain an entry for this guild
                    elif cmd.guild_id not in self._slash_commands[cmd.name].enabled_guilds:
                        _LOGGER.debug("deleting slash command %r from guild %r", cmd.name, str(cmd.guild_id))
                        await cmd.delete()
                    else:
                        # We are assuming here that all the guild commands with the same name have the same
                        # implementation so that we don't have to do a million more checks
                        if cmd.name in remaining_guild_cmds:
                            remaining_guild_cmds[cmd.name][1].append(cmd.guild_id)
                        else:
                            remaining_guild_cmds[cmd.name] = [cmd, [cmd.guild_id]]
        else:
            for cmd_name, cmds in guild_slash_commands.items():
                for cmd, guild_id in cmds:
                    if cmd.name in remaining_guild_cmds:
                        remaining_guild_cmds[cmd.name][1].append(guild_id)
                    else:
                        remaining_guild_cmds[cmd.name] = [cmd, [guild_id]]

        def compare_commands(
            lb_cmd: slash_commands.TopLevelSlashCommandBase,
            hk_cmd: hikari.Command,
            _guild_ids: typing.Optional[typing.List] = None,
        ) -> bool:
            # If one command is global and the other isn't
            if lb_cmd.enabled_guilds != guild_ids and (lb_cmd.enabled_guilds is None or _guild_ids is None):
                return False

            # If both commands are global
            if _guild_ids is None and lb_cmd.enabled_guilds is None:
                return _serialise_command(lb_cmd) == _serialise_command(hk_cmd)

            # If both commands are guild commands and for the same guilds
            if set(lb_cmd.enabled_guilds) == set(_guild_ids):
                return _serialise_command(lb_cmd) == _serialise_command(hk_cmd)

            # None of the above
            return False

        # Check if existing slash commands have changed before creating any. If a command does not appear
        # to have changed then we don't send the api request to discord to prevent unnecessary rate-limiting and
        # to prevent the 1h wait period when creating global commands
        if self._recreate_changed_slash_commands:
            for cmd in remaining_globals.values():
                if cmd.name not in self._slash_commands:
                    continue

                if not compare_commands(self._slash_commands[cmd.name], cmd):
                    _LOGGER.debug("recreating global slash command %r as it appears to have changed", cmd.name)
                    await self._slash_commands[cmd.name].auto_create(self._app)
                else:
                    _LOGGER.debug(
                        "not recreating global slash command %r as it doesn't appear to have changed", cmd.name
                    )

            for cmd, guild_ids in remaining_guild_cmds.values():
                if cmd.name not in self._slash_commands:
                    continue

                if not compare_commands(self._slash_commands[cmd.name], cmd, guild_ids):
                    _LOGGER.debug("recreating guild slash command %r as it appears to have changed", cmd.name)
                    await self._slash_commands[cmd.name].auto_create(self._app)
                else:
                    _LOGGER.debug(
                        "not recreating guild slash command %r as it doesn't appear to have changed", cmd.name
                    )

        all_cmd_names = [
            *[c.name for c in remaining_globals.values()],
            *[c.name for c, _ in remaining_guild_cmds.values()],
        ]
        for cmd_name, cmd in self._slash_commands.items():
            if cmd_name not in all_cmd_names:
                _LOGGER.debug("creating slash command %r as it does not seem to exist yet", cmd_name)
                await cmd.auto_create(self._app)
