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

__all__ = ["Plugin"]

import typing as t
from collections import defaultdict

import hikari

if t.TYPE_CHECKING:
    from lightbulb_v2 import app as app_
    from lightbulb_v2 import commands


class Plugin:
    def __init__(self, name: str, description: t.Optional[str] = None) -> None:
        self.name = name
        self.description = description or ""

        self._raw_commands: t.List[commands.base.CommandLike] = []
        self._all_commands: t.List[commands.base.Command] = []

        self._listeners: t.MutableMapping[
            t.Type[hikari.Event], t.List[t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]]
        ] = defaultdict(list)

        self._app: t.Optional[app_.BotApp] = None

    @property
    def app(self) -> t.Optional[app_.BotApp]:
        return self._app

    @app.setter
    def app(self, val: app_.BotApp) -> None:
        self._app = val
        # Commands need the BotApp instance in order to be instantiated
        # so we wait until the instance is injected in order to create the Command instanced
        self.create_commands()

    def create_commands(self) -> None:
        assert self._app is not None
        for command_like in self._raw_commands:
            commands_to_impl: t.Sequence[t.Type[commands.base.Command]] = getattr(
                command_like.callback, "__cmd_types__", []
            )
            for cmd_type in commands_to_impl:
                cmd = cmd_type(self._app, command_like)
                cmd.plugin = self
                self._all_commands.append(cmd)

    def command(
        self, cmd_like: t.Optional[commands.base.CommandLike] = None
    ) -> t.Union[commands.base.CommandLike, t.Callable[[commands.base.CommandLike], commands.base.CommandLike]]:
        if cmd_like is not None:
            self._raw_commands.append(cmd_like)
            return cmd_like

        def decorate(cmd_like_: commands.base.CommandLike) -> commands.base.CommandLike:
            self.command(cmd_like_)
            return cmd_like_

        return decorate

    def listener(
        self,
        event: t.Type[hikari.Event],
        listener_func: t.Optional[t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]] = None,
    ) -> t.Union[
        t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]],
        t.Callable[
            [t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]],
            t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]],
        ],
    ]:
        if listener_func is not None:
            self._listeners[event].append(listener_func)
            return listener_func

        def decorate(
            func: t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]
        ) -> t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]:
            # TODO - allow getting event type from type hint
            self.listener(event, func)
            return func

        return decorate
