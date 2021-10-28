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

__all__ = ["Context", "ApplicationContext", "OptionsProxy", "ResponseProxy"]

import abc
import typing as t

import hikari

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb import commands


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


class ResponseProxy:
    """
    Proxy for context responses. Allows fetching of the message created from the response
    lazily instead of a follow-up request being made immediately.
    """

    __slots__ = ("_message", "_fetcher")

    def __init__(
        self,
        message: t.Optional[hikari.Message] = None,
        fetcher: t.Optional[t.Callable[[], t.Coroutine[t.Any, t.Any, hikari.Message]]] = None,
    ) -> None:
        if message is None and fetcher is None:
            raise ValueError("One of message or fetcher arguments cannot be None")
        self._message = message
        self._fetcher = fetcher

    async def message(self) -> hikari.Message:
        """
        Fetches and/or returns the created message from the context response.

        Returns:
            :obj:`~hikari.messages.Message`: The response's created message.
        """
        if self._message is not None:
            return self._message
        assert self._fetcher is not None
        msg = await self._fetcher()
        return msg


class Context(abc.ABC):
    """
    Abstract base class for all context types.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the context is linked to.
    """

    __slots__ = ("_app",)

    def __init__(self, app: app_.BotApp):
        self._app = app

    @property
    def interaction(self) -> t.Optional[hikari.CommandInteraction]:
        # Just to keep the interfaces the same for prefix commands and application commands
        return None

    @property
    def resolved(self) -> t.Optional[hikari.ResolvedOptionData]:
        # Just to keep the interfaces the same for prefix commands and application commands
        return None

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
    def raw_options(self) -> t.Dict[str, t.Any]:
        """Dictionary of :obj:`str` option name to option value that the user invoked the command with."""
        return {}

    @property
    def options(self) -> OptionsProxy:
        """:obj:`~OptionsProxy` wrapping the options that the user invoked the command with."""
        return OptionsProxy(self.raw_options)

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
        """The command name or alias was used in the context."""
        ...

    @property
    @abc.abstractmethod
    def prefix(self) -> str:
        """The prefix that was used in the context."""

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

    async def invoke(self) -> None:
        """
        Invokes the context's command under the current context.

        Returns:
            ``None``
        """
        if self.command is None:
            raise TypeError("This context cannot be invoked - no command was resolved.")  # TODO?
        await self.command.invoke(self)

    @abc.abstractmethod
    async def respond(self, *args: t.Any, **kwargs: t.Any) -> ResponseProxy:
        """
        Create a response to this context.
        """
        ...


class ApplicationContext(Context, abc.ABC):
    __slots__ = ("_event", "_interaction", "_command", "initial_response_sent")

    def __init__(
        self, app: app_.BotApp, event: hikari.InteractionCreateEvent, command: commands.base.ApplicationCommand
    ) -> None:
        super().__init__(app)
        self._event = event
        assert isinstance(event.interaction, hikari.CommandInteraction)
        self._interaction: hikari.CommandInteraction = event.interaction
        self._command = command

        self.initial_response_sent: bool = False
        """Whether or not the initial response has been sent for this interaction."""

    @property
    @abc.abstractmethod
    def command(self) -> commands.base.ApplicationCommand:
        ...

    @property
    def event(self) -> hikari.InteractionCreateEvent:
        return self._event

    @property
    def interaction(self) -> hikari.CommandInteraction:
        return self._interaction

    @property
    def channel_id(self) -> hikari.Snowflakeish:
        return self._interaction.channel_id

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflakeish]:
        return self._interaction.guild_id

    @property
    def member(self) -> t.Optional[hikari.Member]:
        return self._interaction.member

    @property
    def author(self) -> hikari.User:
        return self._interaction.user

    @property
    def invoked_with(self) -> str:
        return self._command.name

    @property
    def command_id(self) -> hikari.Snowflake:
        return self._interaction.command_id

    @property
    def resolved(self) -> t.Optional[hikari.ResolvedOptionData]:
        return self._interaction.resolved

    def get_channel(self) -> t.Optional[t.Union[hikari.GuildChannel, hikari.Snowflake]]:
        if self.guild_id is not None:
            return self.app.cache.get_guild_channel(self.channel_id)
        return self.app.cache.get_dm_channel_id(self.user)

    async def respond(self, *args: t.Any, **kwargs: t.Any) -> ResponseProxy:
        """
        Create a response for this context. The first time this method is called, the initial
        interaction response will be created by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.create_initial_response` with the response
        type set to :obj:`~hikari.interactions.base_interactions.ResponseType.MESSAGE_CREATE` if not otherwise
        specified.

        Subsequent calls will instead create followup responses to the interaction by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.execute`.

        Args:
            *args (Any): Positional arguments passed to ``CommandInteraction.create_initial_response`` or
                ``CommandInteraction.execute``.
            **kwargs: Keyword arguments passed to ``CommandInteraction.create_initial_response`` or
                ``CommandInteraction.execute``.

        Returns:
            :obj:`~ResponseProxy`: Proxy wrapping the response of the ``respond`` call.
        """
        if self.initial_response_sent:
            msg = await self._interaction.execute(*args, **kwargs)
            return ResponseProxy(msg)

        if args and not isinstance(args[0], hikari.ResponseType):
            kwargs["content"] = args[0]
            kwargs.setdefault("response_type", hikari.ResponseType.MESSAGE_CREATE)
        await self._interaction.create_initial_response(**kwargs)
        return ResponseProxy(fetcher=self._interaction.fetch_initial_response)
