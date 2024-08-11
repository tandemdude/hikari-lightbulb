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

__all__ = ["BaseComponent"]

import abc
import typing as t

import hikari
from hikari.api import special_endpoints

from lightbulb import context
from lightbulb.internal import constants

if t.TYPE_CHECKING:
    from collections.abc import Sequence

RowT = t.TypeVar("RowT", special_endpoints.MessageActionRowBuilder, special_endpoints.ModalActionRowBuilder)


class BaseComponent(abc.ABC, t.Generic[RowT]):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def custom_id(self) -> str: ...

    @abc.abstractmethod
    def add_to_row(self, row: RowT) -> RowT: ...


class MessageResponseMixinWithEdit(context.MessageResponseMixin[context.RespondableInteractionT], abc.ABC):
    __slots__ = ()

    async def defer(self, *, ephemeral: bool = False, edit: bool = False) -> None:
        """
        Defer the creation of a response for the interaction that this context represents.

        Args:
            ephemeral: Whether to defer ephemerally (message only visible to the user that triggered
                the command).
            edit: Whether the eventual response should cause an edit instead of creating a new message.

        Returns:
            :obj:`None`
        """
        async with self._response_lock:
            if self._initial_response_sent:
                return

            response_type = (
                hikari.ResponseType.DEFERRED_MESSAGE_UPDATE if edit else hikari.ResponseType.DEFERRED_MESSAGE_CREATE
            )
            await self._create_initial_response(
                response_type,
                flags=hikari.MessageFlag.EPHEMERAL if ephemeral else hikari.MessageFlag.NONE,
            )
            self._initial_response_sent = True

    async def respond(
        self,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        ephemeral: bool = False,
        edit: bool = False,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[special_endpoints.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[Sequence[special_endpoints.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
            edit: Whether the response should cause an edit instead of creating a new message.
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

        Note:
            If this is **not** creating an initial response and ``edit`` is :obj:True`, then this will **always** edit
            the initial response, not the most recently created response.

        See Also:
            :meth:`~MenuContext.edit_response`
            :meth:`~MenuContext.delete_response`
            :meth:`~MenuContext.fetch_response`
        """
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        async with self._response_lock:
            if not self._initial_response_sent:
                await self._create_initial_response(
                    hikari.ResponseType.MESSAGE_UPDATE if edit else hikari.ResponseType.MESSAGE_CREATE,
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
                return constants.INITIAL_RESPONSE_IDENTIFIER
            else:
                if edit:
                    return (
                        await self.edit_response(
                            constants.INITIAL_RESPONSE_IDENTIFIER,
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
                    ).id
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
