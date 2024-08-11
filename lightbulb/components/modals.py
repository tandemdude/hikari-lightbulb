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
import dataclasses
import typing as t
import uuid

import async_timeout
import hikari
from hikari.api import special_endpoints
from hikari.impl import special_endpoints as special_endpoints_impl

from lightbulb.components import base

if t.TYPE_CHECKING:
    from lightbulb import client as client_

ModalComponentT = t.TypeVar("ModalComponentT", bound=base.BaseComponent[special_endpoints.ModalActionRowBuilder])


@dataclasses.dataclass(slots=True, kw_only=True)
class TextInput(base.BaseComponent[special_endpoints.ModalActionRowBuilder]):
    """Dataclass representing a text input."""

    custom_id: str
    """The custom id of the text input."""
    style: hikari.TextInputStyle
    """The style of the text input."""
    label: str
    """The label for the text input."""
    min_length: int
    """The minimum length of the inputted text."""
    max_length: int
    """The maximum length of the inputted text."""
    required: bool
    """Whether the text input is required to be filled."""
    value: hikari.UndefinedOr[str]
    """The default value of the text input."""
    placeholder: hikari.UndefinedOr[str]
    """The placeholder value for the text input."""

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


@dataclasses.dataclass(slots=True, kw_only=True)
class ModalContext(base.MessageResponseMixinWithEdit[hikari.ModalInteraction]):
    """Dataclass representing the context for a modal interaction."""

    modal: Modal
    """The modal this context is for."""
    interaction: hikari.ModalInteraction
    """The interaction this context is for."""

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


class Modal(base.BuildableComponentContainer[special_endpoints.ModalActionRowBuilder], abc.ABC):
    """Class representing a modal."""

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
                custom_id=custom_id or str(uuid.uuid4()),
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
                custom_id=custom_id or str(uuid.uuid4()),
                style=hikari.TextInputStyle.PARAGRAPH,
                label=label,
                min_length=min_length,
                max_length=max_length,
                required=required,
                value=value,
                placeholder=placeholder,
            )
        )

    async def attach(self, client: client_.Client, custom_id: str, *, timeout: float = 30) -> None:  # noqa: ASYNC109
        """
        Attach this modal to the given client, starting the interaction listener for it.

        Args:
            client: The client to attach this modal to.
            custom_id: The custom ID used when sending the modal response.
            timeout: The number of seconds to wait for the correct modal interaction before timing out.

        Returns:
            :obj:`None`

        Raises:
            :obj:`asyncio.TimeoutError`: If the timeout is exceeded.
        """
        queue: asyncio.Queue[hikari.ModalInteraction] = asyncio.Queue()
        client._modal_queues.add(queue)
        try:
            stopped: bool = False
            async with async_timeout.timeout(timeout):
                while not stopped:
                    interaction = await queue.get()
                    if interaction.custom_id != custom_id:
                        continue

                    context = ModalContext(modal=self, interaction=interaction)
                    await self.on_submit(context)

                    stopped = True
        finally:
            # Unregister queue from client
            client._modal_queues.remove(queue)

    @abc.abstractmethod
    async def on_submit(self, ctx: ModalContext) -> None:
        """
        The method to call when the modal is submitted. This **must** be overridden by subclasses.

        Args:
            ctx: The context for the modal submission.

        Returns:
            :obj:`None`
        """
