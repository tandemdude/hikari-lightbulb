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
import functools
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

    __slots__ = ("_message", "_fetcher", "_editor", "_editable")

    def __init__(
        self,
        message: t.Optional[hikari.Message] = None,
        fetcher: t.Optional[t.Callable[[], t.Coroutine[t.Any, t.Any, hikari.Message]]] = None,
        editor: t.Optional[t.Callable[[ResponseProxy], t.Coroutine[t.Any, t.Any, hikari.Message]]] = None,
        editable: bool = True,
    ) -> None:
        if message is None and fetcher is None:
            raise ValueError("One of message or fetcher arguments cannot be None")

        self._message = message
        self._fetcher = fetcher
        self._editor = editor
        self._editable = editable

        if editor is None:

            async def _default_editor(rp: ResponseProxy, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
                return await (await rp.message()).edit(*args, **kwargs)

            self._editor = _default_editor

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

    async def edit(self, *args: t.Any, **kwargs: t.Any) -> hikari.Message:
        """
        Edits the message that this object is proxying. Shortcut for :obj:`hikari.messages.Message.edit`.

        Args:
            *args: Args passed in to :obj:`hikari.messages.Message.edit`
            **kwargs: Kwargs passed in to :obj:`hikari.messages.Message.edit`

        Returns:
            :obj:`~hikari.messages.Message`: New message after edit.

        Raises:
            :obj:`RuntimeError`: This response cannot be edited (for ephemeral interaction followup responses).
        """
        if not self._editable:
            raise RuntimeError("This response does not support editing.")

        assert self._editor is not None
        out = await self._editor(self, *args, **kwargs)
        assert isinstance(out, hikari.Message)
        return out

    async def delete(self) -> None:
        """
        Deletes the message that this object is proxying.

        Returns:
            ``None``
        """
        msg = await self.message()
        await msg.delete()


class Context(abc.ABC):
    """
    Abstract base class for all context types.

    Args:
        app (:obj:`~.app.BotApp`): The ``BotApp`` instance that the context is linked to.
    """

    __slots__ = ("_app", "_responses", "_responded", "_deferred", "_invoked")

    def __init__(self, app: app_.BotApp):
        self._app = app
        self._responses: t.List[ResponseProxy] = []
        self._responded: bool = False
        self._deferred: bool = False
        self._invoked: t.Optional[commands.base.Command] = None

    @abc.abstractmethod
    async def _maybe_defer(self) -> None:
        ...

    @property
    def deferred(self) -> bool:
        """Whether or not the response from this context is currently deferred."""
        return self._deferred

    @property
    def responses(self) -> t.List[ResponseProxy]:
        """List of all previous responses sent for this context."""
        return self._responses

    @property
    def previous_response(self) -> t.Optional[ResponseProxy]:
        """The last response sent for this context."""
        return self._responses[-1] if self._responses else None

    @property
    def interaction(self) -> t.Optional[hikari.CommandInteraction]:
        """The interaction that triggered this context. Will be ``None`` for prefix commands."""
        # Just to keep the interfaces the same for prefix commands and application commands
        return None

    @property
    def resolved(self) -> t.Optional[hikari.ResolvedOptionData]:
        """The resolved option data for this context. Will be ``None`` for prefix commands"""
        # Just to keep the interfaces the same for prefix commands and application commands
        return None

    @property
    def app(self) -> app_.BotApp:
        """The ``BotApp`` instance the context is linked to."""
        return self._app

    @property
    def bot(self) -> app_.BotApp:
        """Alias for :obj:`~Context.app`"""
        return self.app

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
    def attachments(self) -> t.Sequence[hikari.Attachment]:
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
        """The root command object that the context is for."""
        ...

    @property
    def invoked(self) -> t.Optional[commands.base.Command]:
        """The command or subcommand that was invoked in this context."""
        return self._invoked

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
            raise TypeError("This context cannot be invoked - no command was resolved.")
        await self._maybe_defer()
        await self.command.invoke(self)

    @abc.abstractmethod
    async def respond(self, *args: t.Any, **kwargs: t.Any) -> ResponseProxy:
        """
        Create a response to this context.
        """
        ...

    async def edit_last_response(self, *args: t.Any, **kwargs: t.Any) -> t.Optional[hikari.Message]:
        """
        Edit the most recently sent response. Shortcut for :obj:`hikari.messages.Message.edit`.

        Args:
            *args: Args passed to :obj:`hikari.messages.Message.edit`.
            **kwargs: Kwargs passed to :obj:`hikari.messages.Message.edit`.

        Returns:
            Optional[:obj:`~hikari.messages.Message`]: New message after edit, or ``None`` if no responses have
                been sent for the context yet.
        """
        if not self._responses:
            return None

        return await self._responses[-1].edit(*args, **kwargs)

    async def delete_last_response(self) -> None:
        """
        Delete the most recently send response. Shortcut for :obj:`hikari.messages.Message.delete`.

        Returns:
            ``None``
        """
        if not self._responses:
            return

        await self._responses.pop().delete()


class ApplicationContext(Context, abc.ABC):
    __slots__ = ("_event", "_interaction", "_command")

    def __init__(
        self, app: app_.BotApp, event: hikari.InteractionCreateEvent, command: commands.base.ApplicationCommand
    ) -> None:
        super().__init__(app)
        self._event = event
        assert isinstance(event.interaction, hikari.CommandInteraction)
        self._interaction: hikari.CommandInteraction = event.interaction
        self._command = command

    async def _maybe_defer(self) -> None:
        if self._command.auto_defer:
            await self.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)

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
    def attachments(self) -> t.Sequence[hikari.Attachment]:
        return []

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
        kwargs.pop("reply", None)
        kwargs.pop("mentions_reply", None)
        kwargs.pop("nonce", None)

        if self._command.default_ephemeral:
            kwargs.setdefault("flags", hikari.MessageFlag.EPHEMERAL)

        if self._responded:
            kwargs.pop("response_type", None)
            if args and isinstance(args[0], hikari.ResponseType):
                args = args[1:]

            self._responses.append(ResponseProxy(await self._interaction.execute(*args, **kwargs), editable=False))
            self._deferred = False
            return self._responses[-1]

        if args:
            if not isinstance(args[0], hikari.ResponseType):
                kwargs["content"] = args[0]
                kwargs.setdefault("response_type", hikari.ResponseType.MESSAGE_CREATE)
            else:
                kwargs["response_type"] = args[0]
                if len(args) > 1:
                    kwargs.setdefault("content", args[1])
        else:
            kwargs.setdefault("response_type", hikari.ResponseType.MESSAGE_CREATE)

        kwargs.pop("attachment", None)
        kwargs.pop("attachments", None)

        await self._interaction.create_initial_response(**kwargs)

        async def _editor(
            rp: ResponseProxy, *args_: t.Any, inter: hikari.CommandInteraction, **kwargs_: t.Any
        ) -> hikari.Message:
            await inter.edit_initial_response(*args_, **kwargs_)
            return await rp.message()

        self._responses.append(
            ResponseProxy(
                fetcher=self._interaction.fetch_initial_response,
                editor=functools.partial(_editor, inter=self._interaction)
                if hikari.MessageFlag.EPHEMERAL in kwargs.get("flags", hikari.MessageFlag.NONE)
                else None,
            )
        )
        self._responded = True

        if kwargs["response_type"] in (
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            hikari.ResponseType.DEFERRED_MESSAGE_UPDATE,
        ):
            self._deferred = True

        return self._responses[-1]
