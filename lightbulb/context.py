# -*- coding: utf-8 -*-
#
# api_ref_gen::add_autodoc_option::inherited-members
#
# Copyright (c) 2023-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

__all__ = ["AutocompleteContext", "Context", "MessageResponseMixin"]

import abc
import asyncio
import typing as t
from collections.abc import Mapping
from collections.abc import Sequence

import hikari
from hikari.api import special_endpoints

from lightbulb.internal import constants

if t.TYPE_CHECKING:
    from lightbulb import client as client_
    from lightbulb import commands

T = t.TypeVar("T", int, str, float)
RespondableInteractionT = t.TypeVar(
    "RespondableInteractionT", hikari.CommandInteraction, hikari.ComponentInteraction, hikari.ModalInteraction
)
AutocompleteResponse: t.TypeAlias = t.Union[
    Sequence[special_endpoints.AutocompleteChoiceBuilder],
    Sequence[T],
    Mapping[str, T],
    Sequence[tuple[str, T]],
]


class AutocompleteContext(t.Generic[T]):
    """Class representing the context for an autocomplete interaction."""

    __slots__ = ("_focused", "_initial_response_sent", "client", "command", "interaction", "options")

    def __init__(
        self,
        client: client_.Client,
        interaction: hikari.AutocompleteInteraction,
        options: Sequence[hikari.AutocompleteInteractionOption],
        command: type[commands.CommandBase],
        initial_response_sent: asyncio.Event,
    ) -> None:
        self.client: client_.Client = client
        """The client that created the context."""
        self.interaction: hikari.AutocompleteInteraction = interaction
        """The interaction for the autocomplete invocation."""
        self.options: Sequence[hikari.AutocompleteInteractionOption] = options
        """The options provided with the autocomplete interaction."""
        self.command: type[commands.CommandBase] = command
        """Command class for the autocomplete invocation."""

        self._focused: hikari.AutocompleteInteractionOption | None = None
        self._initial_response_sent: asyncio.Event = initial_response_sent

    @property
    def focused(self) -> hikari.AutocompleteInteractionOption:
        """
        The focused option for the autocomplete interaction - the option currently being autocompleted.

        See Also:
            :meth:`~AutocompleteContext.get_option`
        """
        if self._focused is not None:
            return self._focused

        found = next(filter(lambda opt: opt.is_focused, self.options))

        self._focused = found
        return self._focused

    @property
    def initial_response_sent(self) -> asyncio.Event:
        """
        The event that will be set when an initial response is sent for this context.

        .. versionadded:: 3.0.2
        """
        return self._initial_response_sent

    def get_option(self, name: str) -> hikari.AutocompleteInteractionOption | None:
        """
        Get the option with the given name if available. If the option has localization enabled, you should
        use its localization key.

        Args:
            name: The name of the option to get.

        Returns:
            The option, or :obj:`None` if not available from the interaction.

        See Also:
            :obj:`~AutocompleteContext.focused`
        """
        option = self.command._command_data.options.get(name)
        if option is None:
            return None

        return next(filter(lambda opt: opt.name == option._localized_name, self.options), None)

    @staticmethod
    def _normalise_choices(choices: AutocompleteResponse[T]) -> Sequence[special_endpoints.AutocompleteChoiceBuilder]:
        if isinstance(choices, Mapping):
            return [hikari.impl.AutocompleteChoiceBuilder(name=k, value=v) for k, v in choices.items()]

        def _to_command_choice(
            item: special_endpoints.AutocompleteChoiceBuilder | tuple[str, T] | T,
        ) -> special_endpoints.AutocompleteChoiceBuilder:
            if isinstance(item, special_endpoints.AutocompleteChoiceBuilder):
                return item

            if isinstance(item, (str, int, float)):
                return hikari.impl.AutocompleteChoiceBuilder(name=str(item), value=item)

            return hikari.impl.AutocompleteChoiceBuilder(name=item[0], value=item[1])

        return list(map(_to_command_choice, choices))

    async def respond(self, choices: AutocompleteResponse[T]) -> None:
        """
        Create a response for the autocomplete interaction this context represents.

        Args:
            choices: The choices to respond to the interaction with.

        Returns:
            :obj:`None`
        """
        normalised_choices = self._normalise_choices(choices)
        await self.interaction.create_response(normalised_choices)
        self._initial_response_sent.set()


class MessageResponseMixin(abc.ABC, t.Generic[RespondableInteractionT]):
    """Abstract mixin for contexts that allow creating responses to interactions."""

    __slots__ = ("_initial_response_sent", "_response_lock")

    def __init__(self, initial_response_sent: asyncio.Event) -> None:
        self._response_lock: asyncio.Lock = asyncio.Lock()
        self._initial_response_sent: asyncio.Event = initial_response_sent

    @property
    @abc.abstractmethod
    def interaction(self) -> RespondableInteractionT:
        """The interaction that this context is for."""

    @property
    def initial_response_sent(self) -> asyncio.Event:
        """The event that will be set when an initial response is sent for this context."""
        return self._initial_response_sent

    async def edit_response(
        self,
        response_id: hikari.Snowflakeish,
        content: hikari.UndefinedNoneOr[t.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish | hikari.Attachment] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[Sequence[hikari.Resourceish | hikari.Attachment]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialUser] | bool] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialRole] | bool] = hikari.UNDEFINED,
    ) -> hikari.Message:
        """
        Edit the response with the given identifier.

        Args:
            response_id: The identifier of the response to delete - as returned by :meth:`~Context.respond`.
            content: The message contents.
            attachment: The message attachment.
            attachments: The message attachments.
            component: The builder object of the component to include in this message.
            components: The sequence of the component builder objects to include in this message.
            embed: The message embed.
            embeds: The message embeds.
            mentions_everyone: Whether the message should parse @everyone/@here mentions.
            user_mentions: The user mentions to include in the message.
            role_mentions: The role mentions to include in the message.

        Returns:
            :obj:`~hikari.messages.Message`: The updated message object for the response with the given identifier.

        Note:
            This documentation does not contain a full description of the parameters as they would just
            be copy-pasted from the hikari documentation. See
            :meth:`~hikari.interactions.base_interactions.MessageResponseMixin.edit_initial_response` for a more
            detailed description.
        """
        if response_id == constants.INITIAL_RESPONSE_IDENTIFIER:
            return await self.interaction.edit_initial_response(
                content,
                attachment=attachment,
                attachments=attachments,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )
        return await self.interaction.edit_message(
            response_id,
            content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )

    async def delete_response(self, response_id: hikari.Snowflakeish) -> None:
        """
        Delete the response with the given identifier.

        Args:
            response_id: The identifier of the response to delete - as returned by :meth:`~Context.respond`.

        Returns:
            :obj:`None`
        """
        if response_id == constants.INITIAL_RESPONSE_IDENTIFIER:
            return await self.interaction.delete_initial_response()
        return await self.interaction.delete_message(response_id)

    async def fetch_response(self, response_id: hikari.Snowflakeish) -> hikari.Message:
        """
        Fetch the message object for the response with the given identifier.

        Args:
            response_id: The identifier of the response to fetch - as returned by :meth:`~Context.respond`.

        Returns:
            :obj:`~hikari.messages.Message`: The message for the response with the given identifier.
        """
        if response_id == constants.INITIAL_RESPONSE_IDENTIFIER:
            return await self.interaction.fetch_initial_response()
        return await self.interaction.fetch_message(response_id)

    async def _create_initial_response(
        self,
        response_type: hikari.ResponseType,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[Sequence[hikari.Embed]] = hikari.UNDEFINED,
        poll: hikari.UndefinedOr[special_endpoints.PollBuilder] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialUser] | bool] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialRole] | bool] = hikari.UNDEFINED,
    ) -> hikari.Snowflakeish:
        await self.interaction.create_initial_response(
            response_type,  # type: ignore[reportArgumentType]
            content,
            flags=flags,
            tts=tts,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            poll=poll,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )
        return constants.INITIAL_RESPONSE_IDENTIFIER

    async def defer(self, *, ephemeral: bool = False) -> None:
        """
        Defer the creation of a response for the interaction that this context represents.

        Args:
            ephemeral: Whether to defer ephemerally (message only visible to the user that triggered
                the command).

        Returns:
            :obj:`None`
        """
        async with self._response_lock:
            if self._initial_response_sent.is_set():
                return

            await self._create_initial_response(
                hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
                flags=hikari.MessageFlag.EPHEMERAL if ephemeral else hikari.MessageFlag.NONE,
            )
            self._initial_response_sent.set()

    async def respond(
        self,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        ephemeral: bool = False,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[Sequence[hikari.Embed]] = hikari.UNDEFINED,
        poll: hikari.UndefinedOr[special_endpoints.PollBuilder] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialUser] | bool] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialRole] | bool] = hikari.UNDEFINED,
    ) -> hikari.Snowflakeish:
        """
        Create a response to the interaction that this context represents.

        Args:
            content: The message contents.
            ephemeral: Whether the message should be ephemeral (only visible to the user that triggered the command).
                This is just a convenience argument - passing ``flags=hikari.MessageFlag.EPHEMERAL`` will function
                the same way.
            attachment: The message attachment.
            attachments: The message attachments.
            component: The builder object of the component to include in this message.
            components: The sequence of the component builder objects to include in this message.
            embed: The message embed.
            embeds: The message embeds.
            poll: The poll to include with the message.
            flags: The message flags this response should have.
            tts: Whether the message will be read out by a screen reader using Discord's TTS (text-to-speech) system.
            mentions_everyone: Whether the message should parse @everyone/@here mentions.
            user_mentions: The user mentions to include in the message.
            role_mentions: The role mentions to include in the message.

        Returns:
            :obj:`hikari.snowflakes.Snowflakeish`: An identifier for the response. This can then be used to edit,
                delete, or fetch the response message using the appropriate methods.

        Note:
            This documentation does not contain a full description of the parameters as they would just
            be copy-pasted from the hikari documentation. See
            :meth:`~hikari.interactions.base_interactions.MessageResponseMixin.create_initial_response` for a more
            detailed description.

        See Also:
            :meth:`~MessageResponseMixin.edit_response`
            :meth:`~MessageResponseMixin.delete_response`
            :meth:`~MessageResponseMixin.fetch_response`
        """
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        async with self._response_lock:
            if not self._initial_response_sent.is_set():
                await self._create_initial_response(
                    hikari.ResponseType.MESSAGE_CREATE,
                    content,
                    flags=flags,
                    tts=tts,
                    attachment=attachment,
                    attachments=attachments,
                    component=component,
                    components=components,
                    embed=embed,
                    embeds=embeds,
                    poll=poll,
                    mentions_everyone=mentions_everyone,
                    user_mentions=user_mentions,
                    role_mentions=role_mentions,
                )
                self._initial_response_sent.set()
                return constants.INITIAL_RESPONSE_IDENTIFIER
            else:
                # This will automatically cause a response if the initial response was deferred previously.
                # I am not sure if this is intentional by discord however so, we may want to look into changing
                # this to actually edit the initial response if it was previously deferred.
                return (
                    await self.interaction.execute(
                        content,
                        flags=flags,
                        tts=tts,
                        attachment=attachment,
                        attachments=attachments,
                        component=component,
                        components=components,
                        embed=embed,
                        embeds=embeds,
                        poll=poll,
                        mentions_everyone=mentions_everyone,
                        user_mentions=user_mentions,
                        role_mentions=role_mentions,
                    )
                ).id


class Context(MessageResponseMixin[hikari.CommandInteraction]):
    """Class representing the context for a single command invocation."""

    __slots__ = ("_interaction", "client", "command", "options")

    def __init__(
        self,
        client: client_.Client,
        interaction: hikari.CommandInteraction,
        options: Sequence[hikari.CommandInteractionOption],
        command: commands.CommandBase,
        initial_response_sent: asyncio.Event,
    ) -> None:
        super().__init__(initial_response_sent)

        self.client: client_.Client = client
        """The client that created the context."""
        self._interaction: hikari.CommandInteraction = interaction
        self.options: Sequence[hikari.CommandInteractionOption] = options
        """The options to use for the command invocation."""
        self.command: commands.CommandBase = command
        """Command instance for the command invocation."""

        self.command._set_context(self)

    @property
    def interaction(self) -> hikari.CommandInteraction:
        """The interaction for the command invocation."""
        return self._interaction

    @property
    def guild_id(self) -> hikari.Snowflake | None:
        """The ID of the guild that the command was invoked in. :obj:`None` if the invocation occurred in DM."""
        return self.interaction.guild_id

    @property
    def channel_id(self) -> hikari.Snowflake:
        """The ID of the channel that the command was invoked in."""
        return self.interaction.channel_id

    @property
    def user(self) -> hikari.User:
        """The user that invoked the command."""
        return self.interaction.user

    @property
    def member(self) -> hikari.InteractionMember | None:
        """The member that invoked the command, if it was invoked in a guild."""
        return self.interaction.member

    @property
    def command_data(self) -> commands.CommandData:
        """The metadata for the invoked command."""
        return self.command._command_data

    async def respond_with_modal(
        self,
        title: str,
        custom_id: str,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
    ) -> None:
        """
        Create a modal response to the interaction that this context represents.

        Args:
            title: The title that will show up in the modal.
            custom_id: Developer set custom ID used for identifying interactions with this modal.
            component: A component builder to send in this modal.
            components: A sequence of component builders to send in this modal.

        Returns:
            :obj:`None`

        Raises:
            :obj:`RuntimeError`: If an initial response has already been sent.
        """
        async with self._response_lock:
            if self._initial_response_sent.is_set():
                raise RuntimeError("cannot respond with a modal if an initial response has already been sent")

            await self.interaction.create_modal_response(title, custom_id, component, components)
            self._initial_response_sent.set()
