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

__all__ = ["BaseComponent", "BuildableComponentContainer", "MessageResponseMixinWithEdit"]

import abc
import typing as t
from collections.abc import Sequence

import hikari
from hikari.api import special_endpoints

from lightbulb import context
from lightbulb.internal import constants

if t.TYPE_CHECKING:
    import typing_extensions as t_ex

RowT = t.TypeVar("RowT", special_endpoints.MessageActionRowBuilder, special_endpoints.ModalActionRowBuilder)
BaseComponentT = t.TypeVar("BaseComponentT", bound="BaseComponent[t.Any]")


class BaseComponent(abc.ABC, t.Generic[RowT]):
    """Abstract base class for a component that can be added to an action row builder."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def custom_id(self) -> str:
        """The custom ID for this component."""

    @abc.abstractmethod
    def add_to_row(self, row: RowT) -> RowT:
        """
        Add this component to the given action row builder, and return the updated builder.

        Args:
            row: The row to add the component to.

        Returns:
            The updated builder.
        """


class MessageResponseMixinWithEdit(context.MessageResponseMixin[context.RespondableInteractionT], abc.ABC):
    """
    Abstract mixin derived from ``MessageResponseMixin`` that additionally allows creating an initial response of
    type :obj:`hikari.interactions.base_interactions.ResponseType.MESSAGE_UPDATE` (and the deferred variant).
    """

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
            if self._initial_response_sent.is_set():
                return

            response_type = (
                hikari.ResponseType.DEFERRED_MESSAGE_UPDATE if edit else hikari.ResponseType.DEFERRED_MESSAGE_CREATE
            )
            await self._create_initial_response(
                response_type,
                flags=hikari.MessageFlag.EPHEMERAL if ephemeral else hikari.MessageFlag.NONE,
            )
            self._initial_response_sent.set()

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
            edit: Whether the response should cause an edit instead of creating a new message.
            attachment: The message attachment.
            attachments: The message attachments.
            component: The builder object of the component to include in this message.
            components: The sequence of the component builder objects to include in this message.
            embed: The message embed.
            embeds: The message embeds.
            poll: The poll to include with the message. Ignored when ``edit=True``.
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

        Note:
            If this is **not** creating an initial response and ``edit`` is :obj:`True`, then this will **always** edit
            the initial response, not the most recently created response.

        See Also:
            :meth:`~lightbulb.context.MessageResponseMixin.edit_response`
            :meth:`~lightbulb.context.MessageResponseMixin.delete_response`
            :meth:`~lightbulb.context.MessageResponseMixin.fetch_response`
        """
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        async with self._response_lock:
            if not self._initial_response_sent.is_set():
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
                    poll=hikari.UNDEFINED if edit else poll,
                    mentions_everyone=mentions_everyone,
                    user_mentions=user_mentions,
                    role_mentions=role_mentions,
                )
                self._initial_response_sent.set()
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
                        poll=poll,
                        mentions_everyone=mentions_everyone,
                        user_mentions=user_mentions,
                        role_mentions=role_mentions,
                    )
                ).id


class BuildableComponentContainer(abc.ABC, Sequence[special_endpoints.ComponentBuilder], t.Generic[RowT]):
    """
    Abstract base class allowing subclasses to be used as containers for :obj:`~BaseComponent`s, as well
    as being passed to the ``components=`` kwarg of respond methods.

    This class does not require ``super().__init__()`` to be called within subclasses.
    """

    __slots__ = ("__current_row", "__rows")

    __current_row: int
    __rows: list[list[BaseComponent[RowT]]]

    @property
    def _current_row(self) -> int:
        try:
            return self.__current_row
        except AttributeError:
            self.__current_row = 0
        return self.__current_row

    @property
    def _rows(self) -> list[list[BaseComponent[RowT]]]:
        try:
            return self.__rows
        except AttributeError:
            self.__rows = [[] for _ in range(self._max_rows)]
        return self.__rows

    @t.overload
    def __getitem__(self, item: int) -> special_endpoints.ComponentBuilder: ...

    @t.overload
    def __getitem__(self, item: slice) -> Sequence[special_endpoints.ComponentBuilder]: ...

    def __getitem__(
        self, item: int | slice
    ) -> special_endpoints.ComponentBuilder | Sequence[special_endpoints.ComponentBuilder]:
        return self._build().__getitem__(item)

    def __len__(self) -> int:
        return sum(1 for row in self._rows if row)

    def _build(self) -> Sequence[special_endpoints.ComponentBuilder]:
        built_rows: list[special_endpoints.ComponentBuilder] = []
        for row in self._rows:
            if not row:
                continue

            bld = self._make_action_row()
            for component in row:
                bld = component.add_to_row(bld)
            built_rows.append(bld)
        return built_rows

    def clear_rows(self) -> t_ex.Self:
        """Remove all components from this container."""
        for row in self._rows:
            row.clear()
        return self

    def clear_current_row(self) -> t_ex.Self:
        """Remove all components from the current row."""
        self._rows[self._current_row].clear()
        return self

    def next_row(self) -> t_ex.Self:
        """Move the current row pointer to the next row."""
        if self._current_row + 1 >= self._max_rows:
            raise RuntimeError("the maximum number of rows has been reached")
        self.__current_row += 1
        return self

    def previous_row(self) -> t_ex.Self:
        """Move the current row pointer back to the previous row."""
        self.__current_row = max(0, self._current_row - 1)
        return self

    def add(self, component: BaseComponentT) -> BaseComponentT:
        """
        Adds the given component to the container.

        Args:
            component: The component to add.

        Returns:
            The added component.
        """
        if self._current_row_full():
            self.next_row()

        self._rows[self._current_row].append(component)
        return component

    @property
    @abc.abstractmethod
    def _max_rows(self) -> int:
        """The maximum number of rows allowed for this container."""

    @abc.abstractmethod
    def _make_action_row(self) -> RowT:
        """Create and return an instance of the row type needed for the components to be added to."""

    @abc.abstractmethod
    def _current_row_full(self) -> bool:
        """Whether the current row is full. Used during layout to know when to advance to the next row."""
