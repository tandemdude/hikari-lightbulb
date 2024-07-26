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

__all__ = ["AutocompleteContext", "Context", "RestContext"]

import asyncio
import collections.abc
import dataclasses
import os
import typing as t

import hikari
from hikari import files
from hikari.api import special_endpoints
from hikari.impl import special_endpoints as special_endpoints_impl

if t.TYPE_CHECKING:
    from lightbulb import client as client_
    from lightbulb import commands

T = t.TypeVar("T", int, str, float)
AutocompleteResponse: t.TypeAlias = t.Union[
    t.Sequence[special_endpoints.AutocompleteChoiceBuilder],
    t.Sequence[T],
    t.Mapping[str, T],
    t.Sequence[tuple[str, T]],
]

INITIAL_RESPONSE_IDENTIFIER: t.Final[int] = -1


@dataclasses.dataclass(slots=True)
class AutocompleteContext(t.Generic[T]):
    """Dataclass representing the context for an autocomplete interaction."""

    client: client_.Client
    """The client that created the context."""

    interaction: hikari.AutocompleteInteraction
    """The interaction for the autocomplete invocation."""
    options: t.Sequence[hikari.AutocompleteInteractionOption]
    """The options provided with the autocomplete interaction."""

    command: type[commands.CommandBase]
    """Command class for the autocomplete invocation."""

    _focused: hikari.AutocompleteInteractionOption | None = dataclasses.field(init=False, default=None)

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
    def _normalise_choices(choices: AutocompleteResponse[T]) -> t.Sequence[special_endpoints.AutocompleteChoiceBuilder]:
        if isinstance(choices, collections.abc.Mapping):
            return [hikari.impl.AutocompleteChoiceBuilder(name=k, value=v) for k, v in choices.items()]

        def _to_command_choice(
            item: t.Union[
                special_endpoints.AutocompleteChoiceBuilder,
                tuple[str, T],
                T,
            ],
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


@dataclasses.dataclass(slots=True)
class RestAutocompleteContext(AutocompleteContext[T]):
    _initial_response_callback: t.Callable[
        [hikari.api.InteractionAutocompleteBuilder],
        None,
    ]

    async def respond(self, choices: AutocompleteResponse[T]) -> None:
        normalised_choices = self._normalise_choices(choices)
        self._initial_response_callback(special_endpoints_impl.InteractionAutocompleteBuilder(normalised_choices))


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

    async def edit_response(
        self,
        response_id: hikari.Snowflakeish,
        content: hikari.UndefinedNoneOr[t.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish | hikari.Attachment] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[t.Sequence[hikari.Resourceish | hikari.Attachment]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
            response_id: The identifier of the response to delete - as returned by :meth:`~Context.respond`.

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
            response_id: The identifier of the response to fetch - as returned by :meth:`~Context.respond`.

        Returns:
            :obj:`~hikari.messages.Message`: The message for the response with the given identifier.
        """
        if response_id == INITIAL_RESPONSE_IDENTIFIER:
            return await self.interaction.fetch_initial_response()
        return await self.interaction.fetch_message(response_id)

    async def _create_initial_response(
        self,
        response_type: t.Literal[hikari.ResponseType.MESSAGE_CREATE, hikari.ResponseType.DEFERRED_MESSAGE_CREATE],
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[t.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialUser] | bool] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialRole] | bool] = hikari.UNDEFINED,
    ) -> hikari.Snowflakeish:
        await self.interaction.create_initial_response(
            response_type,
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
        return INITIAL_RESPONSE_IDENTIFIER

    async def defer(self, ephemeral: bool = False) -> None:
        """
        Defer the creation of a response for the interaction that this context represents.

        Args:
            ephemeral: Whether to defer ephemerally (message only visible to the user that triggered
                the command).

        Returns:
            :obj:`None`
        """
        async with self._response_lock:
            if self._initial_response_sent:
                return

            await self._create_initial_response(
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
            title: The title that will show up in the modal.
            custom_id: Developer set custom ID used for identifying interactions with this modal.
            component: A component builder to send in this modal.
            components: A sequence of component builders to send in this modal.

        Returns:
            :obj:`None`
        """
        async with self._response_lock:
            if self._initial_response_sent:
                return

            await self.interaction.create_modal_response(title, custom_id, component, components)
            self._initial_response_sent = True

    async def respond(
        self,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        ephemeral: bool = False,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[t.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialUser] | bool] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialRole] | bool] = hikari.UNDEFINED,
    ) -> hikari.Snowflakeish:
        """
        Create a response to the interaction that this context represents.

        Args:
            content: The message contents.
            ephemeral: Whether the message should be ephemeral (only visible to the user that triggered the command).
                This is just a convenience argument - passing `flags=hikari.MessageFlag.EPHEMERAL` will function
                the same way.
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
            :obj:`hikari.snowflakes.Snowflakeish`: An identifier for the response. This can then be used to edit,
                delete, or fetch the response message using the appropriate methods.

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
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        async with self._response_lock:
            if not self._initial_response_sent:
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
                ).id


@dataclasses.dataclass(slots=True)
class RestContext(Context):
    _initial_response_callback: t.Callable[
        [hikari.api.InteractionResponseBuilder],
        None,
    ]

    async def respond_with_modal(
        self,
        title: str,
        custom_id: str,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
    ) -> None:
        if component is hikari.UNDEFINED and components is hikari.UNDEFINED:
            raise ValueError("either 'component' or 'components' must be provided")

        components = components or ([component] if component is not hikari.UNDEFINED else hikari.UNDEFINED)
        assert components is not hikari.UNDEFINED

        async with self._response_lock:
            if self._initial_response_sent:
                return

            self._initial_response_callback(
                special_endpoints_impl.InteractionModalBuilder(title, custom_id, list(components))
            )
            self._initial_response_sent = True

    async def _create_initial_response(
        self,
        response_type: hikari.ResponseType,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[t.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[t.Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[t.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialUser] | bool] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialRole] | bool] = hikari.UNDEFINED,
    ) -> hikari.Snowflakeish:
        if attachment and attachments:
            raise ValueError("You may only specify one of 'attachment' or 'attachments', not both")
        if component and components:
            raise ValueError("You may only specify one of 'component' or 'components', not both")
        if embed and embeds:
            raise ValueError("You may only specify one of 'embed' or 'embeds', not both")

        if not (embed or embeds) and isinstance(content, hikari.Embed):
            embed = content
            content = hikari.UNDEFINED
        elif not (attachment or attachments) and isinstance(content, (files.Resource, files.RAWISH_TYPES, os.PathLike)):
            attachment = content
            content = hikari.UNDEFINED

        attachments_ = [*(attachments or []), *([attachment] if attachment else [])]
        components_ = [*(components or []), *([component] if component else [])]
        embeds_ = [*(embeds or []), *([embed] if embed else [])]

        bld: t.Union[hikari.api.InteractionDeferredBuilder, hikari.api.InteractionMessageBuilder]
        if response_type is hikari.ResponseType.MESSAGE_CREATE:
            bld = special_endpoints_impl.InteractionMessageBuilder(
                response_type,
                str(content),
                flags=flags,
                is_tts=tts,
                mentions_everyone=mentions_everyone,
                role_mentions=role_mentions,
                user_mentions=user_mentions,
                attachments=attachments_,
                components=components_,
                embeds=embeds_,
            )
        elif response_type is hikari.ResponseType.DEFERRED_MESSAGE_CREATE:
            bld = special_endpoints_impl.InteractionDeferredBuilder(response_type, flags=flags)
        else:
            raise TypeError("unexpected response_type passed")

        self._initial_response_callback(bld)
        return INITIAL_RESPONSE_IDENTIFIER
