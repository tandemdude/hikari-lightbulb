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

import typing
import functools
import collections
import inspect

import hikari
from hikari.events import message

from lightbulb import commands
from lightbulb import context
from lightbulb import errors
from lightbulb import stringview
from lightbulb import plugins

if typing.TYPE_CHECKING:
    from hikari.models import messages


async def _return_prefix(
    _, __, *, prefixes: typing.Union[str, typing.List[str], typing.Tuple[str]]
) -> typing.Union[str, typing.List[str], typing.Tuple[str]]:
    return prefixes


class BotWithHandler(hikari.Bot):
    """
    A subclassed implementation of :class:`hikari.impl.bot.BotAppImpl` which contains a command handler.
    This should be instantiated instead of the superclass if you want to be able to use 
    the command handler implementation provided.

    The prefix argument will accept any of the following:

    - A single string, eg ``'!'``

    - An iterable (such as a list) of strings, eg ``['!', '?']``

    - A function or coroutine that takes **only** two arguments, ``bot`` and ``message``, and that returns a single string or iterable of strings.

    Args:
        prefix: The bot's command prefix, iterable of prefixes, or callable that returns a prefix or iterable of prefixes.
        ignore_bots (:obj:`bool`): Whether or not the bot should ignore its commands when invoked by other bots. Defaults to ``True``.
        owner_ids (List[ :obj:`int` ]): IDs that the bot should treat as owning the bot.
        **kwargs: Other parameters passed to the :class:`hikari.impl.bot.BotAppImpl` constructor.
    """

    def __init__(
        self,
        *,
        prefix: typing.Union[
            typing.Iterable[str],
            typing.Callable[
                [BotWithHandler, messages.Message],
                typing.Union[
                    typing.Callable[
                        [BotWithHandler, messages.Message], typing.Iterable[str],
                    ],
                    typing.Coroutine[None, typing.Any, typing.Iterable[str]],
                ],
            ],
        ],
        ignore_bots: bool = True,
        owner_ids: typing.Iterable[int] = (),
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.event_dispatcher.subscribe(message.MessageCreateEvent, self.handle)

        if isinstance(prefix, str):
            self.get_prefix = functools.partial(_return_prefix, prefixes=[prefix])
        elif isinstance(prefix, collections.abc.Iterable):
            self.get_prefix = functools.partial(_return_prefix, prefixes=prefix)
        else:
            self.get_prefix = prefix

        self.ignore_bots: bool = ignore_bots
        self.owner_ids: typing.Iterable[int] = owner_ids

        self.extensions = {}
        self.plugins: typing.MutableMapping[str, plugins.Plugin] = {}
        self.commands: typing.MutableMapping[
            str, typing.Union[commands.Command, commands.Group]
        ] = {}

    async def _default_command_error(self, event: errors.CommandErrorEvent) -> None:
        raise event.error

    async def fetch_owner_ids(self) -> None:
        """
        Fetches the IDs of the bot's owner(s) from the API and stores them in
        :attr:`.command_handler.BotWithHandler.owner_ids`

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

    def command(
        self, *, allow_extra_arguments: bool = True, name: typing.Optional[str] = None
    ) -> typing.Callable:
        """
        A decorator that registers a callable as a command for the handler.

        Args:
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (:obj:`str`): Optional name of the command. Defaults to the name of the function if not specified.

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(token="token_here", prefix="!")

                @bot.command()
                async def ping(ctx):
                    await ctx.reply("Pong!")

        See Also:
            :meth:`.command_handler.BotWithHandler.add_command`
        """
        registered_commands = self.commands

        def decorate(func: typing.Callable):
            nonlocal registered_commands
            nonlocal allow_extra_arguments
            nonlocal name
            name = func.__name__ if name is None else name
            if not registered_commands.get(name):
                registered_commands[name] = commands.Command(
                    func, allow_extra_arguments, name
                )
                return registered_commands[name]

        return decorate

    def group(
        self, *, allow_extra_arguments: bool = True, name: typing.Optional[str] = None
    ) -> typing.Callable:
        """
        A decorator that registers a callable as a command group for the handler.

        Args:
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (:obj:`str`): Optional name of the command. Defaults to the name of the function if not specified.

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(token="token_here", prefix="!")

                @bot.group()
                async def foo(ctx):
                    await ctx.reply("Bar")

        See Also:
            :meth:`.commands.Group.command` for how to add subcommands to a group.
        """
        registered_commands = self.commands

        def decorate(func: typing.Callable):
            nonlocal registered_commands
            nonlocal allow_extra_arguments
            nonlocal name
            name = func.__name__ if name is None else name
            if not registered_commands.get(name):
                registered_commands[name] = commands.Group(
                    func, allow_extra_arguments, name
                )
                return registered_commands.get(name)

        return decorate

    def add_command(
        self,
        func: typing.Callable,
        *,
        allow_extra_arguments=True,
        name: typing.Optional[str] = None,
    ) -> None:
        """
        Adds a command to the bot. Similar to the ``command`` decorator.

        Args:
            func (:obj:`typing.Callable`): The function to add as a command.
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (:obj:`str`): Optional name of the command. Defaults to the name of the function if not specified.

        Returns:
            ``None``

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(token="token_here", prefix="!")

                async def ping(ctx):
                    await ctx.reply("Pong!")

                bot.add_command(ping)

        See Also:
            :meth:`.command_handler.BotWithHandler.command`
        """
        name = func.__name__ if name is None else name
        if not self.commands.get(name):
            self.commands[name] = commands.Command(func, allow_extra_arguments, name)

    def add_group(
        self,
        func: typing.Callable,
        *,
        allow_extra_arguments=True,
        name: typing.Optional[str] = None,
    ) -> None:
        """
        Adds a command group to the bot. Similar to the ``group`` decorator.

        Args:
            func (:obj:`typing.Callable`): The function to add as a command group.
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (:obj:`str`): Optional name of the command group. Defaults to the name of the function if not specified.

        Returns:
            ``None``

        See Also:
            :meth:`.command_handler.BotWithHandler.group`
            :meth:`.command_handler.BotWithHandler.add_command`
        """
        name = func.__name__ if name is None else name
        if not self.commands.get(name):
            self.commands[name] = commands.Group(func, allow_extra_arguments, name)

    def add_plugin(self, plugin: plugins.Plugin) -> None:
        """
        Add a :obj:`.plugins.Plugin` to the bot including all of the plugin commands.

        Args:
            plugin (:obj:`.plugins.Plugin`): Plugin to add to the bot.

        Returns:
            ``None``
        """
        self.plugins[plugin.name] = plugin
        self.commands.update(plugin.commands)

    def get_command(self, name: str) -> typing.Optional[commands.Command]:
        """
        Get a command object from its registered name.

        Args:
            name (:obj:`str`): The name of the command to get the object for.

        Returns:
            Optional[ :obj:`.commands.Command` ] command object registered to that name.
        """
        return self.commands.get(name)

    def get_plugin(self, name: str) -> typing.Optional[plugins.Plugin]:
        """
        Get a plugin object from its registered name.

        Args:
             name (:obj:`str`): The name of the plugin to get the object for.

        Returns:
            Optional[ :obj:`.commands.Command` ] plugin object registered to that name.
        """
        return self.plugins.get(name)

    def remove_command(self, name: str) -> typing.Optional[str]:
        """
        Remove a command from the bot and return its name or ``None`` if no command was removed.

        Args:
            name (:obj:`str`): The name of the command to remove.

        Returns:
            Optional[ :obj:`str` ] name of the command that was removed.
        """
        command = self.commands.pop(name)
        return command.name if command is not None else None

    def remove_plugin(self, name: str) -> typing.Optional[str]:
        """
        Remove a plugin from the bot and return its name or ``None`` if no plugin was removed.

        Args:
            name (:obj:`str`): The name of the plugin to remove.

        Returns:
            Optional[ :obj:`str` ] name of the plugin that was removed.
        """
        plugin = self.plugins.pop(name)
        if plugin is not None:
            for k in plugin.commands.keys():
                self.commands.pop(k)
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
            ExtensionAlreadyLoaded: If the extension has already been loaded.
            ExtensionMissingLoad: If the extension to be loaded does not contain a ``load`` function.

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

        module = __import__(extension)

        if "load" not in dir(module):
            raise errors.ExtensionMissingLoad(f"{extension} is missing a load function")
        else:
            module.load(self)
            attributes = []
            for item in dir(module):
                item = getattr(module, item)
                if isinstance(item, commands.Command) or isinstance(
                    item, plugins.Plugin
                ):
                    attributes.append(item)
            self.extensions[extension] = attributes

    def unload_extension(self, extension: str) -> None:
        """
        **NOT IMPLEMENTED YET**
        Watch this space
        """
        raise NotImplementedError

    def resolve_arguments(
        self, message: messages.Message, prefix: str
    ) -> typing.List[str]:
        """
        Resolves the arguments that a command was invoked with from the message containing the invocation.

        Args:
            message (:obj:`hikari.models.messages.Message`): The message to resolve the arguments for.
            prefix (:obj:`str`): The prefix the command was executed with.

        Returns:
            List[ :obj:`str` ] List of the arguments the command was invoked with.

        Note:
            The first item in the list will always contain the prefix+command string which can
            be used to validate if the message was intended to invoke a command and if the command
            they attempted to invoke is actually valid.
        """
        string_view = stringview.StringView(message.content[len(prefix) :])
        return string_view.deconstruct_str()

    async def _evaluate_checks(
        self, command: commands.Command, context: context.Context
    ):
        for check in command.checks:
            try:
                check_pass = await check(context)
                if not check_pass:
                    raise errors.CheckFailure(
                        f"Check {check.__name__} failed for command {context.invoked_with}"
                    )
            except errors.OnlyInGuild as e:
                self.event_dispatcher.dispatch(
                    errors.CommandErrorEvent(e, context.message)
                )
                return False
            except errors.OnlyInDM as e:
                self.event_dispatcher.dispatch(
                    errors.CommandErrorEvent(e, context.message)
                )
                return False
            except errors.NotOwner as e:
                self.event_dispatcher.dispatch(
                    errors.CommandErrorEvent(e, context.message)
                )
                return False
            except errors.CheckFailure as e:
                self.event_dispatcher.dispatch(
                    errors.CommandErrorEvent(e, context.message)
                )
                return False
        return True

    async def _invoke_command(
        self,
        command: commands.Command,
        context: context.Context,
        args: typing.List[str],
    ) -> None:
        if not await self._evaluate_checks(command, context):
            return

        if not command._has_max_args and len(args) >= command._min_args:
            await command(context, *args)

        elif len(args) < command._min_args:
            self.event_dispatcher.dispatch(
                errors.CommandErrorEvent(
                    errors.NotEnoughArguments(context.invoked_with), context.message
                )
            )
            return

        elif len(args) > command._max_args and not command.allow_extra_arguments:
            self.event_dispatcher.dispatch(
                errors.CommandErrorEvent(
                    errors.TooManyArguments(context.invoked_with), context.message
                )
            )
            return

        elif command._max_args == 0:
            await command(context)

        else:
            await command(context, *args[: command._max_args + 1])

    async def handle(self, event: message.MessageCreateEvent) -> None:
        """
        The message listener that deals with validating the invocation messages. If invocation message
        is valid then it will invoke the relevant command.

        Args:
            event (:obj:`hikari.events.message.MessageCreateEvent`): The message create event containing a possible command invocation.

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

        content = event.message.content
        prefix = None
        for p in prefixes:
            if content.startswith(p):
                prefix = p
                break

        if prefix is None:
            return

        args = self.resolve_arguments(event.message, prefix)

        invoked_with = args[0]
        if invoked_with not in self.commands:
            self.event_dispatcher.dispatch(
                errors.CommandErrorEvent(
                    errors.CommandNotFound(invoked_with), event.message
                )
            )
            return

        invoked_command = self.commands[invoked_with]
        if isinstance(invoked_command, commands.Command):
            new_args = args[1:]
        if isinstance(invoked_command, commands.Group):
            invoked_command, new_args = invoked_command.resolve_subcommand(args)

        command_context = context.Context(
            self, event.message, prefix, invoked_with, invoked_command
        )
        await self._invoke_command(invoked_command, command_context, new_args)

    def run(self) -> None:
        if errors.CommandErrorEvent not in self.event_dispatcher._listeners:
            self.event_dispatcher.subscribe(
                errors.CommandErrorEvent, self._default_command_error
            )
        super().run()
