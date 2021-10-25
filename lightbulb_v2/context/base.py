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
    """
    Proxy for the options that the command was invoked with allowing access using
    dot notation instead of dictionary lookup.

    Args:
        options (Dict[:obj:`str`, Any]): Options to act as a proxy for.
    """

    def __init__(self, options: t.Dict[str, t.Any]) -> None:
        self._options = options

    def __getattr__(self, item: str) -> t.Any:
        return self._options.get(item)


class Context(abc.ABC):
    """
    Abstract base class for all context types.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the context is linked to.
    """

    def __init__(self, app: app_.BotApp):
        self._app = app

    @property
    def app(self) -> app_.BotApp:
        """The ``BotApp`` instance the context is linked to."""
        return self._app

    @property
    @abc.abstractmethod
    def event(self) -> t.Union[hikari.MessageCreateEvent, hikari.InteractionCreateEvent]:
        """The event for the context."""
        ...

    @property
    @abc.abstractmethod
    def channel_id(self) -> hikari.Snowflakeish:
        """The channel ID for the context."""
        ...

    @property
    @abc.abstractmethod
    def guild_id(self) -> t.Optional[hikari.Snowflakeish]:
        """The guild ID for the context."""
        ...

    @property
    @abc.abstractmethod
    def member(self) -> t.Optional[hikari.Member]:
        """The member for the context."""
        ...

    @property
    @abc.abstractmethod
    def author(self) -> hikari.User:
        """The author for the context."""
        ...

    @property
    def user(self) -> hikari.User:
        """The user for the context. Alias for :obj:`~Context.author`."""
        return self.author

    @property
    @abc.abstractmethod
    def invoked_with(self) -> str:
        """The command name that the context is for."""
        ...

    @property
    @abc.abstractmethod
    def command(self) -> t.Optional[commands.base.Command]:
        """The command object that the context is for."""
        ...

    @abc.abstractmethod
    def get_channel(self) -> t.Optional[t.Union[hikari.GuildChannel, hikari.Snowflake]]:
        """The channel object for the context's channel ID."""
        ...

    def get_guild(self) -> t.Optional[hikari.Guild]:
        """The guild object for the context's guild ID."""
        if self.guild_id is None:
            return None
        return self.app.cache.get_guild(self.guild_id)

    @abc.abstractmethod
    async def respond(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        """
        Create a response to this context.
        """
        ...
