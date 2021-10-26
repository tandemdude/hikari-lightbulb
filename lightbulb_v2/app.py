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

import functools
import inspect
import sys
import typing as t

import hikari
from hikari.internal import ux

from lightbulb_v2 import checks
from lightbulb_v2 import commands
from lightbulb_v2 import context as context_
from lightbulb_v2 import errors
from lightbulb_v2 import events
from lightbulb_v2 import plugins
from lightbulb_v2.utils import data_store

_PrefixT = t.Union[
    t.Sequence[str],
    t.Callable[["BotApp", hikari.Message], t.Union[t.Sequence[str], t.Coroutine[t.Any, t.Any, t.Sequence[str]]]],
]


def when_mentioned_or(
    prefix_provider: _PrefixT,
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

            app = lightbulb.Bot(prefix=lightbulb.when_mentioned_or(get_prefix), ...)
    """

    async def get_prefixes(app: BotApp, message: hikari.Message) -> t.Sequence[str]:
        me = app.get_me()
        assert me is not None
        mentions = [f"<@{me.id}> ", f"<@!{me.id}> "]

        if callable(prefix_provider):
            prefixes = prefix_provider(app, message)
            if inspect.iscoroutine(prefixes):
                assert not isinstance(prefixes, t.Sequence)
                prefixes = await prefixes
        else:
            prefixes = prefix_provider

        if isinstance(prefixes, str):
            return mentions + [prefixes]
        elif isinstance(prefixes, t.Sequence):
            return mentions + list(prefixes)
        return mentions

    return get_prefixes


# str is by definition a sequence of str so these type hints are correct
def _default_get_prefix(_: BotApp, __: hikari.Message, *, prefixes: t.Sequence[str]) -> t.Sequence[str]:
    return prefixes


class BotApp(hikari.GatewayBot):
    """
    A subclassed implementation of the :obj:`~hikari.impl.bot.GatewayBot` class containing a command
    handler. This should be instantiated instead of the superclass if you wish to use the command
    handler implementation provided.

    Args:
        token (:obj:`str`): The bot account's token.
        prefix (Optional[PrefixT]): The command prefix to use for prefix commands, or ``None`` if prefix commands
            will not be used.
        ignore_bots (:obj:`bool`): Whether or not prefix commands should ignore bots for invocation. Defaults
            to ``True``.
        owner_ids (Sequence[int]): The IDs of the users that own the bot. If not provided then it will be fetched
            by :obj:`~BotApp.fetch_owner_ids`.
        **kwargs (Any): Additional keyword arguments passed to the constructor of the :obj:`~hikari.impl.bot.GatewayBot`
            class.
    """

    def __init__(
        self,
        token: str,
        prefix: t.Optional[_PrefixT] = None,
        ignore_bots: bool = True,
        owner_ids: t.Sequence[int] = (),
        **kwargs: t.Any,
    ) -> None:
        super().__init__(token, **kwargs)
        # The prefix command handler expects an iterable to be returned from the get_prefix function
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
        self.ignore_bots = ignore_bots
        """Whether or not other bots will be ignored when invoking prefix commands."""
        self.owner_ids = owner_ids
        """The owner ID(s) for the owner(s) of the bot account."""

        self.application: t.Optional[hikari.Application] = None
        """The :obj:`~hikari.applications.Application` for the bot account. This will always be ``None`` before the bot has logged in."""

        self.d = data_store.DataStore()
        """A :obj:`~.utils.data_store.DataStore` instance enabling storage of custom data without subclassing."""

        self._prefix_commands: t.MutableMapping[str, commands.prefix.PrefixCommand] = {}
        self._slash_commands: t.MutableMapping[str, commands.slash.SlashCommand] = {}
        self._message_commands: t.MutableMapping[str, commands.message.MessageCommand] = {}
        self._user_commands: t.MutableMapping[str, commands.user.UserCommand] = {}

        self._plugins: t.MutableMapping[str, plugins.Plugin] = {}

        self._checks: t.List[checks.Check] = []

        if prefix is not None:
            self.subscribe(hikari.MessageCreateEvent, self.handle_messsage_create_for_prefix_commands)

    @staticmethod
    def print_banner(banner: t.Optional[str], allow_color: bool, force_color: bool) -> None:
        ux.print_banner(banner, allow_color, force_color)
        if banner == "hikari":
            sys.stdout.write("Thank you for using lightbulb!\n")

    async def fetch_owner_ids(self) -> t.Sequence[hikari.SnowflakeishOr[int]]:
        """
        Fetch the bot's owner IDs, or return the given owner IDs on instantiation if provided.

        Returns:
            Sequence[SnowflakeishOr[:obj:`int`]]: The IDs of the bot's owners.
        """
        if self.owner_ids:
            return self.owner_ids

        self.application = self.application or await self.rest.fetch_application()

        owner_ids = []
        if self.application.owner is not None:
            owner_ids.append(self.application.owner.id)
        if self.application.team is not None:
            owner_ids.extend([member_id for member_id in self.application.team.members])
        return owner_ids

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

    async def maybe_dispatch_error_event(
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

        if not handled:
            if self.get_listeners(type(event), polymorphic=True):
                await self.dispatch(event)
                handled = True

        return handled

    def get_prefix_command(self, name: str) -> t.Optional[commands.prefix.PrefixCommand]:
        """
        Gets the prefix command with the given name, or ``None`` if no command with that name was found.

        Args:
            name (:obj:`str`): Name of the prefix command to get.

        Returns:
            Optional[:obj:`~.commands.prefix.PrefixCommand`]: Prefix command object with the given name, or ``None``
                if not found.
        """
        return self._prefix_commands.get(name)

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

    def add_command(
        self, cmd_like: t.Optional[commands.base.CommandLike] = None
    ) -> t.Union[commands.base.CommandLike, t.Callable[[commands.base.CommandLike], commands.base.CommandLike]]:
        """
        Alias for :obj:`~BotApp.command`.
        """
        return self.command(cmd_like)

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
            for command_cls in commands_to_impl:
                cmd = command_cls(self, cmd_like)

                if cmd.is_subcommand:
                    continue

                self._add_command_to_correct_attr(cmd)

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

    def get_plugin(self, name: str) -> t.Optional[plugins.Plugin]:
        """
        Gets the plugin with the given name, or ``None`` if no plugin with that name was found.

        Args:
            name (:obj:`str`): Name of the plugin to get.

        Returns:
            Optional[:obj:`~.plugins.Plugin`]: Plugin object with the given name, or ``None`` if not found.
        """
        return self._plugins.get(name)

    def add_plugin(self, plugin: plugins.Plugin) -> None:
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

    def remove_plugin(self, plugin_or_name: t.Union[plugins.Plugin, str]) -> None:
        """
        Unregisters a plugin from the bot, removing all commands and listeners
        present in the plugin.

        Args:
            plugin_or_name (Union[:obj:`~.plugins.Plugin`, :obj:`str`]): Plugin or name of the plugin
                to unregister from the bot.

        Returns:
            ``None``
        """
        plugin: t.Optional[t.Union[plugins.Plugin, str]] = plugin_or_name
        if isinstance(plugin, str):
            plugin = self.get_plugin(plugin)

        if plugin is None:
            return

        for command in plugin._raw_commands:
            self.remove_command(command)
        for event, listeners in plugin._listeners.items():
            for listener in listeners:
                self.unsubscribe(event, listener)

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
            assert not isinstance(prefixes, t.Sequence)
            prefixes = await prefixes
        prefixes = t.cast(t.Sequence[str], prefixes)

        if isinstance(prefixes, str):
            prefixes = [prefixes]
        prefixes = sorted(prefixes, key=len, reverse=True)

        invoked_prefix = None
        for prefix in prefixes:
            if event.message.content.startswith(prefix):
                invoked_prefix = prefix
                break

        if invoked_prefix is None:
            return None

        new_content = event.message.content[len(invoked_prefix) :]
        if not new_content or new_content.isspace():
            return None

        split_content = new_content.split(maxsplit=1)
        invoked_with, _ = split_content[0], "".join(split_content[1:])

        if not invoked_with:
            return None

        command = self.get_prefix_command(invoked_with)

        return cls(self, event, command, invoked_with, invoked_prefix)

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

        await context.command.invoke(context)

    async def handle_messsage_create_for_prefix_commands(self, event: hikari.MessageCreateEvent) -> None:
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
            new_exc = t.cast(errors.LightbulbError, new_exc)
            error_event = events.PrefixCommandErrorEvent(app=self, exception=new_exc, context=context)
            handled = await self.maybe_dispatch_error_event(error_event, [getattr(context.command, "error_handler")])

            if not handled:
                raise new_exc
        else:
            assert context.command is not None
            await self.dispatch(events.PrefixCommandCompletionEvent(app=self, command=context.command, context=context))
