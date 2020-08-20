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

__all__: typing.Final[typing.List[str]] = ["Bot"]

import collections
import functools
import importlib
import inspect
import logging
import sys
import typing

import hikari
from multidict import CIMultiDict

from lightbulb import commands
from lightbulb import context
from lightbulb import errors
from lightbulb import help as help_command
from lightbulb import plugins
from lightbulb import stringview

_LOGGER = logging.getLogger("lightbulb")


async def _return_prefix(
    _, __, *, prefixes: typing.Union[str, typing.List[str], typing.Tuple[str]]
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
        self._commands: typing.MutableMapping[
            str, commands.Command
        ] = dict() if not self.insensitive_commands else CIMultiDict()
        self.commands: typing.Set[commands.Command] = set()
        """A set containing all commands and groups registered to the bot."""
        self._checks = []

        self._help_impl = help_class(self)

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

    def add_check(self, func: typing.Callable[[context.Context], typing.Coroutine[None, None, bool]]) -> None:
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
        unique_commands = list(self.commands)
        while unique_commands:
            command = unique_commands.pop()
            if isinstance(command, commands.Group):
                unique_commands.extend(list(command.subcommands))
            yield command

    def resolve_arguments(self, message: hikari.Message, prefix: str) -> typing.List[str]:
        """
        Resolves the arguments that a command was invoked with from the message containing the invocation.

        Args:
            message (:obj:`hikari.messages.Message`): The message to resolve the arguments for.
            prefix (:obj:`str`): The prefix the command was executed with.

        Returns:
            List[ :obj:`str` ]: List of the arguments the command was invoked with.

        Note:
            The first item in the list will always contain the prefix+command string which can
            be used to validate if the message was intended to invoke a command and if the command
            they attempted to invoke is actually valid.
        """
        string_view = stringview.StringView(message.content[len(prefix) :])
        return string_view.deconstruct_str()

    async def _evaluate_checks(self, command: commands.Command, context: context.Context):
        failed_checks = []

        for check in [*self._checks, *command._checks]:
            try:
                if not await check(context):
                    failed_checks.append(
                        errors.CheckFailure(f"Check {check.__name__} failed for command {context.invoked_with}")
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

    async def _invoke_command(
        self, command: commands.Command, context: context.Context, args: typing.List[str],
    ) -> None:
        try:
            if not await self._evaluate_checks(command, context):
                return

            (before_asterisk, param_name,) = command.arg_details._args_and_name_before_asterisk()
            args = self._concatenate_args(args, command)

            if not command.arg_details.has_max_args and len(args) >= command.arg_details.min_args:
                if param_name is not None:
                    await command.invoke(
                        context, *args[:before_asterisk], **{f"{param_name}": args[-1]},
                    )

                else:
                    await command.invoke(context, *args)

            elif len(args) < command.arg_details.min_args:
                raise errors.NotEnoughArguments(context.invoked_with)

            elif len(args) > command.arg_details.max_args and not command._allow_extra_arguments:
                raise errors.TooManyArguments(context.invoked_with)

            elif command.arg_details.max_args == 0:
                await command.invoke(context)

            else:
                if param_name is not None:
                    await command.invoke(
                        context, *args[:before_asterisk], **{f"{param_name}": args[-1]},
                    )
                else:
                    await command.invoke(context, *args[:before_asterisk])
        except errors.CommandError as ex:
            error_event = errors.CommandErrorEvent(
                app=self, exception=ex, context=context, message=context.message, command=command
            )

            if command._error_listener is not None:
                await command._error_listener(error_event)
            if self.get_listeners(errors.CommandErrorEvent, polymorphic=True):
                await self.dispatch(error_event)
            else:
                raise

    def _concatenate_args(self, args: typing.List[str], command: commands.Command):
        # Concatenates arguments for last argument (after asterisk sign)
        new_args = args
        (before_asterisk, param_name,) = command.arg_details._args_and_name_before_asterisk()

        if before_asterisk < len(args) and not command.arg_details.has_max_args and param_name is not None:
            new_args = [
                *args[:before_asterisk],
                " ".join(args[before_asterisk:]),
            ]

        return new_args

    async def handle(self, event: hikari.MessageCreateEvent) -> None:
        """
        The message listener that deals with validating the invocation messages. If invocation message
        is valid then it will invoke the relevant command.

        Args:
            event (:obj:`hikari.events.message.MessageCreateEvent`): The message create event containing
                a possible command invocation.

        Raises:
            TypeError: When function's signature has more than 1 argument required after asterisk symbol.

        Returns:
            ``None``
        """
        if self.ignore_bots and event.message.author.is_bot:
            return

        if not event.message.content:
            return

        prefixes = self.get_prefix(self, event.message)
        if inspect.iscoroutine(prefixes):
            prefixes = await prefixes

        if isinstance(prefixes, str):
            prefixes = [prefixes]

        prefix = None
        for p in prefixes:
            if event.message.content.startswith(p):
                prefix = p
                break

        if prefix is None:
            return

        args = self.resolve_arguments(event.message, prefix)

        invoked_with = args[0].casefold() if self.insensitive_commands else args[0]

        if invoked_with not in self._commands:
            ex = errors.CommandNotFound(invoked_with)
            error_event = errors.CommandErrorEvent(app=self, exception=ex, message=event.message)

            if self.get_listeners(errors.CommandErrorEvent, polymorphic=True):
                await self.dispatch(error_event)
                return
            else:
                raise ex

        invoked_command = self._commands[invoked_with]

        if isinstance(invoked_command, commands.Group):
            try:
                invoked_command, new_args = invoked_command._resolve_subcommand(args)
            except AttributeError:
                new_args = args[1:]
        else:
            new_args = args[1:]

        command_context = context.Context(self, event.message, prefix, invoked_with, invoked_command)
        await self._invoke_command(invoked_command, command_context, new_args)
