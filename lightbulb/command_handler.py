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
from hikari.utilities import ux
from multidict import CIMultiDict

from lightbulb import commands
from lightbulb import context as context_
from lightbulb import errors
from lightbulb import events
from lightbulb import help as help_command
from lightbulb import plugins
from lightbulb import stringview

_LOGGER = logging.getLogger("lightbulb")

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
        mentions = [f"<@{bot.me.id}> ", f"<@!{bot.me.id}> "]

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


def _return_prefix(
    _, __, *, prefixes: typing.Union[str, typing.Iterable[str]]
) -> typing.Union[str, typing.List[str], typing.Tuple[str]]:
    return prefixes


class Bot(hikari.Bot):
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
        **kwargs: Other parameters passed to the :class:`hikari.impl.bot.BotAppImpl` constructor.
    """

    def __init__(
        self,
        *,
        prefix,
        insensitive_commands: bool = False,
        ignore_bots: bool = True,
        owner_ids: typing.Iterable[int] = (),
        help_class: typing.Type[help_command.HelpCommand] = help_command.HelpCommand,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.subscribe(hikari.MessageCreateEvent, self.handle)

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

        self._help_impl = help_class(self)

    @staticmethod
    def print_banner(banner: typing.Optional[str], allow_color: bool, force_color: bool) -> None:
        ux.print_banner(banner, allow_color, force_color)
        if banner == "hikari":
            sys.stdout.write(f"Thank you for using lightbulb!\n")

    @property
    def help_class(self):
        """The instance of the help class used by the bot."""
        return self._help_impl

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
                    await ctx.reply("Pong!")

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
                    await ctx.reply("Bar")

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

                bot = lightbulb.Bot(token="token_here", prefix="!")

                async def ping(ctx):
                    await ctx.reply("Pong!")

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
                raise NameError(f"Command {func.name} has name or alias already registered.")
        else:
            if set(self._commands.keys()).intersection({func.name, *func._aliases}):
                raise NameError(f"Command {func.name} has name or alias already registered.")

        self.commands.add(func)
        self._commands[func.name] = func
        for alias in func._aliases:
            self._commands[alias] = func
        _LOGGER.debug("new command registered: %s", func.name)
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
            raise AttributeError(f"Command {func.name} has name or alias already registered.")

        self.commands.add(func)
        self._commands[func.name] = func
        for alias in func._aliases:
            self._commands[alias] = func
        _LOGGER.debug("new group registered: %s", func.name)
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

    def add_plugin(self, plugin: plugins.Plugin) -> None:
        """
        Add a :obj:`~.plugins.Plugin` to the bot including all of the plugin commands.

        Args:
            plugin (:obj:`~.plugins.Plugin`): Plugin to add to the bot.

        Returns:
            ``None``

        Raises:
            :obj:`NameError`: If the name of the plugin being added conflicts with an
                existing plugin.
        """
        if plugin.name in self.plugins:
            raise NameError(f"A plugin named {plugin.name} is already registered.")

        self.plugins[plugin.name] = plugin
        for command in plugin.commands.values():
            if isinstance(command, commands.Group):
                self.add_group(command)
            else:
                self.add_command(command)

        for event_type, listeners in plugin.listeners.items():
            for listener in listeners:
                callback = listener.__get__(plugin, type(plugin))
                self.subscribe(listener.event_type, callback)
                _LOGGER.debug("new listener registered: %s (%s)", callback.__name__, listener.event_type.__name__)

        _LOGGER.debug("new plugin registered: %s", plugin.name)

    def get_command(self, name: str) -> typing.Optional[commands.Command]:
        """
        Get a command object from its registered name.

        Args:
            name (:obj:`str`): The name of the command to get the object for.

        Returns:
            Optional[ :obj:`~.commands.Command` ]: Command object registered to that name.
        """
        return self._commands.get(name)

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
        command = self._commands.pop(name)
        self.commands.remove(command)
        if command is not None:
            keys_to_remove = [command.name, *command._aliases]
            keys_to_remove.remove(name)
            for key in keys_to_remove:
                self._commands.pop(key)
            _LOGGER.debug("command removed: %s", command.name)
        return command.name if command is not None else None

    def remove_plugin(self, name: str) -> typing.Optional[str]:
        """
        Remove a plugin from the bot and return its name or ``None`` if no plugin was removed.

        Args:
            name (:obj:`str`): The name of the plugin to remove.

        Returns:
            Optional[ :obj:`str` ]: Name of the plugin that was removed.
        """
        plugin = self.plugins.pop(name)
        plugin.plugin_remove()

        if plugin is not None:
            for k in plugin.commands.keys():
                self.remove_command(k)

            for event_type, listeners in plugin.listeners.items():
                for listener in listeners:
                    callback = listener.__get__(plugin, type(plugin))
                    self.unsubscribe(listener.event_type, callback)
                    _LOGGER.debug("listener removed: %s (%s)", callback.__name__, listener.event_type.__name__)

            _LOGGER.debug("plugin removed: %s", plugin.name)
        return plugin.name if plugin is not None else None

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

                from lightbulb import plugins

                class MyPlugin(plugins.Plugin):
                    ...

                def load(bot):
                    bot.add_plugin(MyPlugin())
        """
        if extension in self.extensions:
            raise errors.ExtensionAlreadyLoaded(f"{extension} is already loaded.")

        module = importlib.import_module(extension)

        if not hasattr(module, "load"):
            raise errors.ExtensionMissingLoad(f"{extension} is missing a load function")
        else:
            module.load(self)
            self.extensions.append(extension)
            _LOGGER.debug("new extension loaded: %s", extension)

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

                from lightbulb import plugins

                class MyPlugin(plugins.Plugin):
                    ...

                def load(bot):
                    bot.add_plugin(MyPlugin())

                def unload(bot):
                    bot.remove_plugin("MyPlugin")
        """
        if extension not in self.extensions:
            raise errors.ExtensionNotLoaded(f"{extension} is not loaded.")

        module = importlib.import_module(extension)

        if not hasattr(module, "unload"):
            raise errors.ExtensionMissingUnload(f"{extension} is missing an unload function")
        else:
            module.unload(self)
            self.extensions.remove(extension)
            del sys.modules[extension]
            _LOGGER.debug("extension unloaded: %s", extension)

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
        _LOGGER.debug("reloading extension: %s", extension)
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
            await self.help_class.send_help_overview(context)
        elif isinstance(obj, commands.Group):
            await self.help_class.send_group_help(context, obj)
        elif isinstance(obj, commands.Command):
            await self.help_class.send_command_help(context, obj)
        elif isinstance(obj, plugins.Plugin):
            await self.help_class.send_plugin_help(context, obj)

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
        prefixes = self.get_prefix(self, message)
        if inspect.iscoroutine(prefixes):
            prefixes = await prefixes

        if isinstance(prefixes, str):
            prefixes = [prefixes]

        prefix = None
        for p in prefixes:
            if message.content.startswith(p):
                prefix = p
                break
        return prefix

    def _validate_command_exists(self, invoked_with) -> commands.Command:
        if (command := self.get_command(invoked_with)) is not None:
            return command
        raise errors.CommandNotFound(invoked_with)

    def resolve_args_for_command(
        self, command: commands.Command, raw_arg_string: str
    ) -> typing.Tuple[typing.List[str], typing.Dict[str, str]]:
        """
        Resolve the appropriate command arguments from an unparsed string
        containing the raw command arguments.

        This method can be overridden if you wish to customise how arguments
        are parsed for all the commands. If you override this then it is important that
        it at least returns a tuple containing an empty list if no positional arguments
        were resolved, and an empty dict if no keyword arguments were resolved.

        If you override this method then you may find the :obj:`~.stringview.StringView`
        class useful for extracting the arguments from the raw string and the property
        :obj:`~.command.arg_details` which contains information about the command's arguments
        and which are optional or required.

        Args:
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
        """
        sv = stringview.StringView(raw_arg_string)
        positional_args, remainder = sv.deconstruct_str(max_parse=command.arg_details.maximum_arguments)
        if remainder and command.arg_details.kwarg_name is None and not command._allow_extra_arguments:
            raise errors.TooManyArguments(command.name)
        if len(positional_args) < command.arg_details.minimum_arguments:
            raise errors.NotEnoughArguments(command.name)

        if not remainder:
            remainder = {}
        if remainder and command.arg_details.kwarg_name is not None:
            remainder = {command.arg_details.kwarg_name: remainder}
        return positional_args, remainder

    async def _invoke_command(
        self,
        command: commands.Command,
        context: context_.Context,
        args: typing.Sequence[str],
        kwarg: typing.Mapping[str, str],
    ) -> None:
        if kwarg and command.arg_details.kwarg_name:
            await command.invoke(context, *args, **kwarg)
        elif args:
            await command.invoke(context, *args)
        else:
            await command.invoke(context)

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
        split_args = ARG_SEP_REGEX.split(new_content, maxsplit=1)
        invoked_with, command_args = split_args[0], "".join(split_args[1:])

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
            positional_args, keyword_arg = self.resolve_args_for_command(command, final_args)
            await self._evaluate_checks(command, context)
        except (
            errors.NotEnoughArguments,
            errors.TooManyArguments,
            errors.CheckFailure,
            errors.CommandSyntaxError,
        ) as ex:
            await self._dispatch_command_error_event_from_exception(ex, event.message, context, command)
            return

        try:
            await self._invoke_command(command, context, positional_args, keyword_arg)
        except errors.CommandError as ex:
            await self._dispatch_command_error_event_from_exception(ex, event.message, context, command)
            return
        except Exception as ex:
            new_ex = errors.CommandInvocationError("An error occurred during command invocation.", original=ex)
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
        if self.ignore_bots and event.message.author.is_bot:
            return

        if not event.message.content:
            return

        await self.process_commands_for_event(event)
