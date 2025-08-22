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

__all__ = ["Modal", "ModalContext", "TextInput"]

import abc
import asyncio
import contextvars
import typing as t
import uuid

import async_timeout
import hikari
import linkd
import typing_extensions as t_ex
from hikari.api import special_endpoints
from hikari.impl import special_endpoints as special_endpoints_impl

from lightbulb import context
from lightbulb.components import base
from lightbulb.internal import marker

if t.TYPE_CHECKING:
    from lightbulb import client as client_

R = t_ex.TypeVar("R", default=t.Any)
ModalComponentT = t.TypeVar("ModalComponentT", bound=base.BaseComponent[special_endpoints.ModalActionRowBuilder])

_MISSING = marker.Marker("MISSING")


class TextInput(base.BaseComponent[special_endpoints.ModalActionRowBuilder]):
    """Class representing a text input."""

    __slots__ = ("_custom_id", "label", "max_length", "min_length", "placeholder", "required", "style", "value")

    def __init__(
        self,
        custom_id: str,
        style: hikari.TextInputStyle,
        label: str,
        min_length: int,
        max_length: int,
        required: bool,
        value: hikari.UndefinedOr[str],
        placeholder: hikari.UndefinedOr[str],
    ) -> None:
        self._custom_id: str = custom_id

        self.style: hikari.TextInputStyle = style
        """The style of the text input."""
        self.label: str = label
        """The label for the text input."""
        self.min_length: int = min_length
        """The minimum length of the inputted text."""
        self.max_length: int = max_length
        """The maximum length of the inputted text."""
        self.required: bool = required
        """Whether the text input is required to be filled."""
        self.value: hikari.UndefinedOr[str] = value
        """The default value of the text input."""
        self.placeholder: hikari.UndefinedOr[str] = placeholder
        """The placeholder value for the text input."""

    @property
    def custom_id(self) -> str:
        """The custom id of the text input."""
        return self._custom_id

    def add_to_row(self, row: special_endpoints.ModalActionRowBuilder) -> special_endpoints.ModalActionRowBuilder:
        return row.add_text_input(
            self.custom_id,
            self.label,
            style=self.style,
            placeholder=self.placeholder,
            value=self.value,
            required=self.required,
            min_length=self.min_length,
            max_length=self.max_length,
        )


class ModalContext(context.MessageResponseMixin[hikari.ModalInteraction], t.Generic[R]):
    """Class representing the context for a modal interaction."""

    __slots__ = ("_interaction", "client", "modal")

    def __init__(
        self,
        client: client_.Client,
        modal: Modal[R],
        interaction: hikari.ModalInteraction,
        initial_response_sent: asyncio.Event,
    ) -> None:
        super().__init__(initial_response_sent)

        self.client: client_.Client = client
        """The client that is handling interactions for this context."""
        self.modal: Modal[R] = modal
        """The modal this context is for."""
        self._interaction: hikari.ModalInteraction = interaction

    @property
    def interaction(self) -> hikari.ModalInteraction:
        """The interaction this context is for."""
        return self._interaction

    @property
    def guild_id(self) -> hikari.Snowflake | None:
        """The ID of the guild that the interaction was created in. :obj:`None` if the interaction occurred in DM."""
        return self.interaction.guild_id

    @property
    def channel_id(self) -> hikari.Snowflake:
        """The ID of the channel that the interaction was created in."""
        return self.interaction.channel_id

    @property
    def user(self) -> hikari.User:
        """The user that created the interaction."""
        return self.interaction.user

    @property
    def member(self) -> hikari.InteractionMember | None:
        """The member that created the interaction, if it was created in a guild."""
        return self.interaction.member

    def value_for(self, input: TextInput) -> str | None:
        """
        Get the submitted value for the given text input component.

        Args:
            input: The text input component to get the value for.

        Returns:
            The value submitted for the given text input component, or :obj:`None` if no value was submitted.
        """
        for row in self.interaction.components:
            for component in row:
                if component.custom_id == input.custom_id:
                    return component.value
        return None


class Modal(
    base.BuildableComponentContainer[special_endpoints.ModalActionRowBuilder], t.Generic[R], metaclass=abc.ABCMeta
):
    """Class representing a modal."""

    __slots__ = ()

    @property
    def _max_rows(self) -> int:
        return 5

    def _make_action_row(self) -> special_endpoints.ModalActionRowBuilder:
        return special_endpoints_impl.ModalActionRowBuilder()

    def _current_row_full(self) -> bool:
        # Currently, you are only allowed a single component within each row
        # Maybe Discord will change this in the future
        return bool(self._rows[self._current_row])

    def add_short_text_input(
        self,
        label: str,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        min_length: int = 0,
        max_length: int = 4000,
        required: bool = True,
        value: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        placeholder: hikari.UndefinedOr[str] = hikari.UNDEFINED,
    ) -> TextInput:
        """
        Add a short text input component to this modal.

        Args:
            label: The label for the text input.
            custom_id: The custom ID for the text input. You probably never want to specify this as it should
                be unique across all modals that your application creates. If unspecified, one will be generated
                for you.
            min_length: The minimum length of the inputted text.
            max_length: The maximum length of the inputted text.
            required: Whether the text input is required to be filled.
            value: The default value of the text input.
            placeholder: The placeholder value for the text input.

        Returns:
            The created text input component.
        """
        return self.add(
            TextInput(
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                style=hikari.TextInputStyle.SHORT,
                label=label,
                min_length=min_length,
                max_length=max_length,
                required=required,
                value=value,
                placeholder=placeholder,
            )
        )

    def add_paragraph_text_input(
        self,
        label: str,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        min_length: int = 0,
        max_length: int = 4000,
        required: bool = True,
        value: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        placeholder: hikari.UndefinedOr[str] = hikari.UNDEFINED,
    ) -> TextInput:
        """
        Add a paragraph text input component to this modal.

        Args:
            label: The label for the text input.
            custom_id: The custom ID for the text input. You probably never want to specify this as it should
                be unique across all modals that your application creates. If unspecified, one will be generated
                for you.
            min_length: The minimum length of the inputted text.
            max_length: The maximum length of the inputted text.
            required: Whether the text input is required to be filled.
            value: The default value of the text input.
            placeholder: The placeholder value for the text input.

        Returns:
            The created text input component.
        """
        return self.add(
            TextInput(
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                style=hikari.TextInputStyle.PARAGRAPH,
                label=label,
                min_length=min_length,
                max_length=max_length,
                required=required,
                value=value,
                placeholder=placeholder,
            )
        )

    async def attach(self, client: client_.Client, custom_id: str, *, timeout: float = 30) -> R:
        """
        Attach this modal to the given client, starting the interaction listener for it.

        Args:
            client: The client to attach this modal to.
            custom_id: The custom ID used when sending the modal response.
            timeout: The number of seconds to wait for the correct modal interaction before timing out.

        Returns:
            ``R``: the return value from your ``on_submit`` method.

        Raises:
            :obj:`asyncio.TimeoutError`: If the timeout is exceeded.

        .. versionadded:: 3.0.2
            Allow values returned from ``on_submit`` to be returned from this method.
        """
        stopped = asyncio.Event()
        ctx = contextvars.copy_context()

        # have to use the missing sentinel to prevent an unbound false positive
        r_val: R = _MISSING  # type: ignore[reportAssignmentType]

        async def _handle_interaction(
            interaction: hikari.ModalInteraction, initial_response_sent: asyncio.Event
        ) -> None:
            context = ModalContext(
                client=client, modal=self, interaction=interaction, initial_response_sent=initial_response_sent
            )

            token = linkd.DI_CONTAINER.set(ctx.get(linkd.DI_CONTAINER))
            try:
                nonlocal r_val
                r_val = await self.on_submit(context)
                stopped.set()
            finally:
                linkd.DI_CONTAINER.reset(token)

        client._attached_modals[custom_id] = _handle_interaction
        try:
            async with async_timeout.timeout(timeout):
                await stopped.wait()
                return r_val
        finally:
            client._attached_modals.pop(custom_id)

    @abc.abstractmethod
    async def on_submit(self, ctx: ModalContext[R]) -> R:
        """
        The method to call when the modal is submitted. This **must** be overridden by subclasses.

        Args:
            ctx: The context for the modal submission.

        Returns:
            ``R``: The value you wish to return from the ``attach`` method.

        .. versionadded:: 3.0.2
            Allow values returned from this method to in turn be returned from the ``attach`` method.
        """
