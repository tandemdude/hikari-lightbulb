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
import typing as t

import hikari

from lightbulb_v2 import checks
from lightbulb_v2 import commands
from lightbulb_v2 import context as context_
from lightbulb_v2 import errors
from lightbulb_v2 import plugins

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
    def __init__(
        self,
        token: str,
        prefix: t.Optional[_PrefixT] = None,
        ignore_bots: bool = True,
        owner_ids: t.Sequence[int] = (),
        application_commands_only: bool = False,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(token, **kwargs)

        self.application: t.Optional[hikari.PartialApplication] = None

        if prefix is None and not application_commands_only:
            raise TypeError("'application_commands_only' is False but no prefix was provided.")

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
        self.owner_ids = owner_ids

        self._prefix_commands: t.MutableMapping[str, commands.prefix.PrefixCommand] = {}
        self._slash_commands: t.MutableMapping[str, commands.slash.SlashCommand] = {}
        self._message_commands: t.MutableMapping[str, commands.message.MessageCommand] = {}
        self._user_commands: t.MutableMapping[str, commands.user.UserCommand] = {}

        self._plugins: t.MutableMapping[str, plugins.Plugin] = {}

        self._checks: t.List[checks.Check] = []

        if prefix is not None:
            self.subscribe(hikari.MessageCreateEvent, self.process_prefix_commands)

    def _add_command_to_correct_attr(self, command: commands.base.Command) -> None:
        if isinstance(command, commands.prefix.PrefixCommand):
            self._prefix_commands[command.name] = command
        elif isinstance(command, commands.slash.SlashCommand):
            self._slash_commands[command.name] = command
        elif isinstance(command, commands.message.MessageCommand):
            self._message_commands[command.name] = command
        elif isinstance(command, commands.user.UserCommand):
            self._user_commands[command.name] = command

    def command(
        self, cmd_like: t.Optional[commands.base.CommandLike] = None
    ) -> t.Union[commands.base.CommandLike, t.Callable[[commands.base.CommandLike], commands.base.CommandLike]]:
        """
        Adds a command to the bot. This method can be used as a first or second order decorator, or called
        manually with the :obj:`~.commands.CommandLike` instance to add as a command.
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

    def add_plugin(self, plugin: plugins.Plugin) -> None:
        plugin.app = self
        for command in plugin._all_commands:
            self._add_command_to_correct_attr(command)
        for event, listeners in plugin._listeners.items():
            for listener_func in listeners:
                self.subscribe(event, listener_func)

    def get_prefix_command(self, name: str) -> t.Optional[commands.prefix.PrefixCommand]:
        return self._prefix_commands.get(name)

    async def get_prefix_context(
        self,
        event: hikari.MessageCreateEvent,
        cls: t.Type[context_.prefix.PrefixContext] = context_.prefix.PrefixContext,
    ) -> t.Optional[context_.prefix.PrefixContext]:
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

    async def process_prefix_commands(self, context: t.Optional[context_.prefix.PrefixContext]) -> None:
        if context is None:
            return

        if context.command is None:
            raise errors.CommandNotFound(
                f"A command with name or alias {context.invoked_with!r} does not exist",
                invoked_with=context.invoked_with,
            )

        await context.command.invoke(context)

    async def handle_messsage_create_for_prefix_commands(self, event: hikari.MessageCreateEvent) -> None:
        if self.ignore_bots and not event.is_human:
            return

        if not event.message.content:
            return

        context = await self.get_prefix_context(event)
        try:
            await self.process_prefix_commands(context)
        except Exception as exc:
            new_exc = exc
            if not isinstance(exc, errors.LightbulbError):
                assert context is not None and context.command is not None
                new_exc = errors.CommandInvocationError(
                    f"An error occurred during command {context.command.name!r} invocation", original=exc
                )
            pass  # TODO error handling and event dispatching
