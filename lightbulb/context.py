# -*- coding: utf-8 -*-
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

__all__ = ["AutocompleteContext", "Context"]

import asyncio
import dataclasses
import functools
import typing as t

import hikari

if t.TYPE_CHECKING:
    from hikari.api import special_endpoints

    from lightbulb import client as client_
    from lightbulb import commands


INITIAL_RESPONSE_IDENTIFIER: t.Final[int] = -1


@dataclasses.dataclass(slots=True)
class AutocompleteContext:
    client: client_.Client
    """The client that created the context."""

    interaction: hikari.AutocompleteInteraction
    """The interaction for the autocomplete invocation."""
    options: t.Sequence[hikari.AutocompleteInteractionOption]
    """The options provided with the autocomplete interaction."""

    command: t.Type[commands.CommandBase]
    """Command class for the autocomplete invocation."""

    _focused: t.Optional[hikari.AutocompleteInteractionOption] = dataclasses.field(init=False, default=None)

    @functools.cached_property
    def focused(self) -> hikari.AutocompleteInteractionOption:
        """The focused option for the autocomplete interaction."""
        if self._focused is not None:
            return self._focused

        found = next(filter(lambda opt: opt.is_focused, self.options))

        self._focused = found
        return self._focused


@dataclasses.dataclass(slots=True)
class Context:
    """Dataclass representing the context for a single command invocation."""

    client: client_.Client
    """The client that created the context."""

    interaction: hikari.CommandInteraction
    """The interaction for the command invocation."""
    options: t.Sequence[hikari.CommandInteractionOption]
    """The options to use for the command invocation."""

    command: commands.CommandBase
    """Command instance for the command invocation."""

    _response_lock: asyncio.Lock = dataclasses.field(init=False, default_factory=asyncio.Lock)
    _initial_response_sent: bool = dataclasses.field(init=False, default=False)

    def __post_init__(self) -> None:
        self.command._set_context(self)

    @property
    def guild_id(self) -> t.Optional[hikari.Snowflake]:
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
    def member(self) -> t.Optional[hikari.InteractionMember]:
        """The member that invoked the command, if it was invoked in a guild."""
        return self.interaction.member

    @property
    def command_data(self) -> commands.CommandData:
        """The metadata for the invoked command."""
        return self.command._command_data

    async def edit_response(
        self,
        response_id: hikari.Snowflakeish,
        content: hikari.UndefinedNoneOr[t.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedNoneOr[t.Union[hikari.Resourceish, hikari.Attachment]] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[
            t.Sequence[t.Union[hikari.Resourceish, hikari.Attachment]]
        ] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        """
        Edit the response with the given identifier.

        Args:
            response_id (:obj:`hikari.snowflakes.Snowflakeish`): The identifier of the response to delete - as
                returned by :meth:`~Context.respond`.
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
            :obj:`~hikari.interactions.base_interactions.MessageResponseMixin.edit_initial_response` for a more
            detailed description.
        """
        if response_id == INITIAL_RESPONSE_IDENTIFIER:
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
            response_id (:obj:`hikari.snowflakes.Snowflakeish`): The identifier of the response to delete - as
                returned by :meth:`~Context.respond`.

        Returns:
            :obj:`None`
        """
        if response_id == INITIAL_RESPONSE_IDENTIFIER:
            return await self.interaction.delete_initial_response()
        return await self.interaction.delete_message(response_id)

    async def fetch_response(self, response_id: hikari.Snowflakeish) -> hikari.Message:
        """
        Fetch the message object for the response with the given identifier.

        Args:
            response_id (:obj:`~hikari.snowflakes.Snowflakeish`): The identifier of the response to fetch - as
                returned by :meth:`~Context.respond`.

        Returns:
            :obj:`~hikari.messages.Message`: The message for the response with the given identifier.
        """
        if response_id == INITIAL_RESPONSE_IDENTIFIER:
            return await self.interaction.fetch_initial_response()
        return await self.interaction.fetch_message(response_id)

    async def defer(self, ephemeral: bool = False) -> None:
        """
        Defer the creation of a response for the interaction that this context represents.

        Args:
            ephemeral (:obj:`bool`): Whether to defer ephemerally (message only visible to the user that triggered
                the command).

        Returns:
            :obj:`None`
        """
        async with self._response_lock:
            if self._initial_response_sent:
                return

            await self.interaction.create_initial_response(
                hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
                flags=hikari.MessageFlag.EPHEMERAL if ephemeral else hikari.MessageFlag.NONE,
            )
            self._initial_response_sent = True

    async def respond_with_modal(
        self,
        title: str,
        custom_id: str,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
    ) -> None:
        """
        Create a modal response to the interaction that this context represents.

        Args:
            title (:obj:`str`): The title that will show up in the modal.
            custom_id (:obj:`str`): Developer set custom ID used for identifying interactions with this modal.
            component (:obj:`~hikari.UndefinedOr` [ :obj:`~hikari.api.special_endpoints.ComponentBuilder` ]): A
                component builder to send in this modal.
            components (:obj:`~hikari.UndefinedOr` [ :obj:`~typing.Sequence` [ :obj:`~hikari.api.special_endpoints.ComponentBuilder` ]]): A
                sequence of component builders to send in this modal.

        Returns:
            :obj:`None`
        """  # noqa: E501
        async with self._response_lock:
            if self._initial_response_sent:
                return

            await self.interaction.create_modal_response(title, custom_id, component, components)
            self._initial_response_sent = True

    async def respond(
        self,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        flags: t.Union[int, hikari.MessageFlag, hikari.UndefinedType] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[t.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            t.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Snowflakeish:
        """
        Create a response to the interaction that this context represents.

        Args:
            content: The message contents.
            attachment: The message attachment.
            attachments: The message attachments.
            component: The builder object of the component to include in this message.
            components: The sequence of the component builder objects to include in this message.
            embed: The message embed.
            embeds: The message embeds.
            flags: The message flags this response should have.
            tts: Whether the message will be read out by a screen reader using Discord's TTS (text-to-speech) system.
            mentions_everyone: Whether the message should parse @everyone/@here mentions.
            user_mentions: The user mentions to include in the message.
            role_mentions: The role mentions to include in the message.

        Returns:
            :obj:`hikari.Snowflakeish`: An identifier for the response. This can then be used to edit, delete, or
                fetch the response message using the appropriate methods.

        Note:
            This documentation does not contain a full description of the parameters as they would just
            be copy-pasted from the hikari documentation. See
            :obj:`~hikari.interactions.base_interactions.MessageResponseMixin.create_initial_response` for a more
            detailed description.

        See Also:
            :meth:`~Context.edit_response`
            :meth:`~Context.delete_response`
            :meth:`~Context.fetch_response`
        """
        async with self._response_lock:
            if not self._initial_response_sent:
                await self.interaction.create_initial_response(
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
                    mentions_everyone=mentions_everyone,
                    user_mentions=user_mentions,
                    role_mentions=role_mentions,
                )
                self._initial_response_sent = True
                return INITIAL_RESPONSE_IDENTIFIER
            else:
                # This will automatically cause a response if the initial response was deferred previously.
                # I am not sure if this is intentional by discord however so, we may want to look into changing
                # this to actually edit the initial response if it was previously deferred.
                return (
                    await self.interaction.execute(
                        content,
                        tts=tts,
                        attachment=attachment,
                        attachments=attachments,
                        component=component,
                        components=components,
                        embed=embed,
                        embeds=embeds,
                        mentions_everyone=mentions_everyone,
                        user_mentions=user_mentions,
                        role_mentions=role_mentions,
                        flags=flags,
                    )
                ).id
