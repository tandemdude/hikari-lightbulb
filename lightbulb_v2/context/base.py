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
__all__ = ["Context"]

import abc
import typing as t

import hikari

if t.TYPE_CHECKING:
    from lightbulb_v2 import app


class Context(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    @property
    def app(self) -> app.BotApp:
        pass

    @abc.abstractmethod
    @property
    def channel_id(self) -> hikari.Snowflakeish:
        pass

    @abc.abstractmethod
    @property
    def guild_id(self) -> t.Optional[hikari.Snowflakeish]:
        pass

    @abc.abstractmethod
    @property
    def member(self) -> hikari.Member:
        pass

    @abc.abstractmethod
    @property
    def author(self) -> hikari.User:
        pass

    @property
    def user(self) -> hikari.User:
        return self.author

    @abc.abstractmethod
    @property
    def command_name(self) -> str:
        pass

    @abc.abstractmethod
    @property
    def command(self) -> hikari.UndefinedType:  # TODO
        pass

    @abc.abstractmethod
    def get_channel(self) -> t.Optional[hikari.TextableChannel]:
        pass

    def get_guild(self) -> t.Optional[hikari.Guild]:
        if self.guild_id is None:
            return None
        return self.app.cache.get_guild(self.guild_id)

    @abc.abstractmethod
    async def respond(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        pass
