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
import typing
import typing as t

import hikari

from lightbulb_v2 import checks
from lightbulb_v2 import plugins
from lightbulb_v2 import commands

_PrefixT = t.Union[
    t.Sequence[str],
    t.Callable[["BotApp", hikari.Message], t.Union[t.Sequence[str], t.Coroutine[t.Any, t.Any, t.Sequence[str]]]],
]


def when_mentioned_or(prefix_provider: _PrefixT) -> t.Callable[[BotApp, hikari.Message], t.Coroutine[t.Any, t.Any, t.Sequence[str]]]:
    async def get_prefixes(bot: BotApp, message: hikari.Message) -> t.Sequence[str]:
        me = bot.get_me()
        assert me is not None
        mentions = [f"<@{me.id}> ", f"<@!{me.id}> "]

        if callable(prefix_provider):
            prefixes = prefix_provider(bot, message)
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

        if prefix is None and not application_commands_only:
            raise TypeError("'application_commands_only' is False but no prefix was provided.")

        # The prefix command handler expects an iterable to be returned from the get_prefix function
        # so we have to wrap a single string prefix in a list here.
        prefix = [prefix] if isinstance(prefix, str) else prefix
        if isinstance(prefix, t.Sequence):
            # Create the default get prefix from the passed-in prefixes if a get_prefix function
            # was not provided
            prefix = functools.partial(_default_get_prefix, prefixes=prefix)
        self.get_prefix = prefix
        self.ignore_bots = ignore_bots
        self.owner_ids = owner_ids

        self._prefix_commands: typing.MutableMapping[str, commands.prefix.PrefixCommand] = {}
        self._slash_commands: typing.MutableMapping[str, commands.slash.SlashCommand] = {}
        self._message_commands: typing.MutableMapping[str, commands.message.MessageCommand] = {}
        self._user_commands: typing.MutableMapping[str, commands.user.UserCommand] = {}

        self._plugins: typing.MutableMapping[str, plugins.Plugin] = {}

        self._checks: typing.List[checks.Check] = []
