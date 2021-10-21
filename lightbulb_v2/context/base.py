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

__all__ = ["Context", "OptionsProxy"]

import abc
import typing as t

import hikari

if t.TYPE_CHECKING:
    from lightbulb_v2 import app as app_
    from lightbulb_v2 import commands


class OptionsProxy:
    def __init__(self, options: t.Dict[str, t.Any]) -> None:
        self._options = options

    def __getattr__(self, item: str) -> t.Any:
        return self._options.get(item)


class Context(abc.ABC):
    def __init__(self, app: app_.BotApp):
        self._app = app

    @property
    def app(self) -> app_.BotApp:
        return self._app

    @property
    @abc.abstractmethod
    def event(self) -> t.Union[hikari.MessageCreateEvent, hikari.InteractionCreateEvent]:
        ...

    @property
    @abc.abstractmethod
    def channel_id(self) -> hikari.Snowflakeish:
        ...

    @property
    @abc.abstractmethod
    def guild_id(self) -> t.Optional[hikari.Snowflakeish]:
        ...

    @property
    @abc.abstractmethod
    def member(self) -> t.Optional[hikari.Member]:
        ...

    @property
    @abc.abstractmethod
    def author(self) -> hikari.User:
        ...

    @property
    def user(self) -> hikari.User:
        return self.author

    @property
    @abc.abstractmethod
    def invoked_with(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def command(self) -> commands.base.Command:
        ...

    @abc.abstractmethod
    def get_channel(self) -> t.Optional[t.Union[hikari.GuildChannel, hikari.Snowflake]]:
        ...

    def get_guild(self) -> t.Optional[hikari.Guild]:
        if self.guild_id is None:
            return None
        return self.app.cache.get_guild(self.guild_id)

    @abc.abstractmethod
    async def respond(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        ...
