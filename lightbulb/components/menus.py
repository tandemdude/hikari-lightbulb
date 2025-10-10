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

__all__ = [
    "ChannelSelect",
    "InteractiveButton",
    "LinkButton",
    "MentionableSelect",
    "Menu",
    "MenuContext",
    "MenuHandle",
    "RoleSelect",
    "Select",
    "TextSelect",
    "TextSelectOption",
    "UserSelect",
]

import abc
import asyncio
import contextlib
import contextvars
import typing as t
import uuid

import async_timeout
import hikari
import linkd
from hikari.api import special_endpoints
from hikari.impl import special_endpoints as special_endpoints_impl

from lightbulb.components import base

if t.TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable
    from collections.abc import Sequence

    import typing_extensions as t_ex

    from lightbulb import client as client_

    ValidSelectOptions: t.TypeAlias = t.Union[Sequence["TextSelectOption"], Sequence[str], Sequence[tuple[str, str]]]
    ComponentCallback: t.TypeAlias = Callable[["MenuContext"], Awaitable[None]]

T = t.TypeVar("T")
MessageComponentT = t.TypeVar("MessageComponentT", bound=base.BaseComponent[special_endpoints.MessageActionRowBuilder])

Emojiish: t.TypeAlias = t.Union[hikari.Snowflakeish, str, hikari.Emoji]


class InteractiveButton(base.BaseComponent[special_endpoints.MessageActionRowBuilder]):
    """Class representing an interactive button."""

    __slots__ = ("_custom_id", "callback", "disabled", "emoji", "label", "style")

    def __init__(
        self,
        style: hikari.ButtonStyle,
        custom_id: str,
        label: hikari.UndefinedOr[str],
        emoji: hikari.UndefinedOr[Emojiish],
        disabled: bool,
        callback: ComponentCallback,
    ) -> None:
        self.style: hikari.ButtonStyle = style
        """The style of the button."""

        self._custom_id: str = custom_id

        self.label: hikari.UndefinedOr[str] = label
        """The label for the button."""
        self.emoji: hikari.UndefinedOr[Emojiish] = emoji
        """The emoji for the button."""
        self.disabled: bool = disabled
        """Whether the button is disabled."""
        self.callback: ComponentCallback = callback
        """The callback method to call when the button is pressed."""

    @property
    def custom_id(self) -> str:
        """The custom id of the button."""
        return self._custom_id

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_interactive_button(
            self.style,  # type: ignore[reportArgumentType]
            self.custom_id,
            emoji=self.emoji,
            label=self.label,
            is_disabled=self.disabled,
        )


class LinkButton(base.BaseComponent[special_endpoints.MessageActionRowBuilder]):
    """Dataclass representing a link button."""

    __slots__ = ("disabled", "emoji", "label", "url")

    def __init__(
        self, url: str, label: hikari.UndefinedOr[str], emoji: hikari.UndefinedOr[Emojiish], disabled: bool
    ) -> None:
        self.url: str = url
        """The url the button links to."""
        self.label: hikari.UndefinedOr[str] = label
        """The label for the button."""
        self.emoji: hikari.UndefinedOr[Emojiish] = emoji
        """The emoji for the button."""
        self.disabled: bool = disabled
        """Whether the button is disabled."""

    @property
    def custom_id(self) -> str:
        return "__lightbulb_placeholder__"

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_link_button(
            self.url,
            emoji=self.emoji,
            label=self.label,
            is_disabled=self.disabled,
        )


class Select(t.Generic[T], base.BaseComponent[special_endpoints.MessageActionRowBuilder], abc.ABC):
    """Dataclass representing a generic select menu."""

    __slots__ = ("_custom_id", "callback", "disabled", "max_values", "min_values", "placeholder")

    def __init__(
        self,
        custom_id: str,
        placeholder: hikari.UndefinedOr[str],
        min_values: int,
        max_values: int,
        disabled: bool,
        callback: ComponentCallback,
    ) -> None:
        self._custom_id: str = custom_id

        self.placeholder: hikari.UndefinedOr[str] = placeholder
        """The placeholder for the select menu."""
        self.min_values: int = min_values
        """The minimum number of items that can be selected."""
        self.max_values: int = max_values
        """The maximum number of items that can be selected."""
        self.disabled: bool = disabled
        """Whether the select menu is disabled."""
        self.callback: ComponentCallback = callback
        """The callback method to call when the select menu is submitted."""

    @property
    def custom_id(self) -> str:
        """The custom id of the select menu."""
        return self._custom_id


class TextSelectOption:
    """Class representing an option for a text select menu."""

    __slots__ = ("default", "description", "emoji", "label", "value")

    def __init__(
        self,
        label: str,
        value: str,
        description: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        emoji: hikari.UndefinedOr[Emojiish] = hikari.UNDEFINED,
        default: bool = False,
    ) -> None:
        self.label: str = label
        """The label for the option."""
        self.value: str = value
        """The value of the option."""
        self.description: hikari.UndefinedOr[str] = description
        """The description of the option."""
        self.emoji: hikari.UndefinedOr[Emojiish] = emoji
        """The emoji for the option."""
        self.default: bool = default
        """Whether this option should be set as selected by default."""


class TextSelect(Select[str]):
    """Class representing a select menu with text options."""

    __slots__ = ("options",)

    def __init__(
        self,
        custom_id: str,
        placeholder: hikari.UndefinedOr[str],
        min_values: int,
        max_values: int,
        disabled: bool,
        callback: ComponentCallback,
        options: ValidSelectOptions,
    ) -> None:
        super().__init__(custom_id, placeholder, min_values, max_values, disabled, callback)

        self.options: ValidSelectOptions = options
        """The options for the select menu."""

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        normalised_options: list[TextSelectOption] = []

        for option in self.options:
            if isinstance(option, str):
                normalised_options.append(TextSelectOption(option, option))
            elif isinstance(option, tuple):
                normalised_options.append(TextSelectOption(option[0], option[1]))
            else:
                normalised_options.append(option)

        bld = row.add_text_menu(
            self.custom_id,
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )
        for opt in normalised_options:
            bld = bld.add_option(
                opt.label, opt.value, description=opt.description, emoji=opt.emoji, is_default=opt.default
            )
        return bld.parent


class UserSelect(Select[hikari.User]):
    """Class representing a select menu with user options."""

    __slots__ = ()

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_select_menu(
            hikari.ComponentType.USER_SELECT_MENU,
            self.custom_id,
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


class RoleSelect(Select[hikari.Role]):
    """Class representing a select menu with role options."""

    __slots__ = ()

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_select_menu(
            hikari.ComponentType.ROLE_SELECT_MENU,
            self.custom_id,
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


class MentionableSelect(Select[hikari.Unique]):
    """Class representing a select menu with snowflake options."""

    __slots__ = ()

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_select_menu(
            hikari.ComponentType.MENTIONABLE_SELECT_MENU,
            self.custom_id,
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


class ChannelSelect(Select[hikari.PartialChannel]):
    """Class representing a select menu with channel options."""

    __slots__ = ("channel_types",)

    def __init__(
        self,
        custom_id: str,
        placeholder: hikari.UndefinedOr[str],
        min_values: int,
        max_values: int,
        disabled: bool,
        callback: ComponentCallback,
        channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]],
    ) -> None:
        super().__init__(custom_id, placeholder, min_values, max_values, disabled, callback)

        self.channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]] = channel_types
        """Channel types permitted to be shown as options."""

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_channel_menu(
            self.custom_id,
            channel_types=self.channel_types or (),
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


class MenuContext(base.MessageResponseMixinWithEdit[hikari.ComponentInteraction]):
    """Class representing the context for an invocation of a component that belongs to a menu."""

    __slots__ = (
        "_interaction",
        "_should_re_resolve_custom_ids",
        "_stop_event",
        "_timeout",
        "client",
        "component",
        "menu",
    )

    def __init__(
        self,
        client: client_.Client,
        menu: Menu,
        interaction: hikari.ComponentInteraction,
        component: base.BaseComponent[special_endpoints.MessageActionRowBuilder],
        _timeout: async_timeout.Timeout | None,
        _stop_event: asyncio.Event,
        _initial_response_sent: asyncio.Event,
    ) -> None:
        super().__init__(_initial_response_sent)

        self.client: client_.Client = client
        """The client that is handling interactions for this context."""
        self.menu: Menu = menu
        """The menu that this context is for."""
        self._interaction: hikari.ComponentInteraction = interaction
        self.component: base.BaseComponent[special_endpoints.MessageActionRowBuilder] = component
        """The component that triggered the interaction for this context."""

        self._timeout: async_timeout.Timeout | None = _timeout
        self._stop_event: asyncio.Event = _stop_event
        self._should_re_resolve_custom_ids: bool = False

    @property
    def interaction(self) -> hikari.ComponentInteraction:
        """The interaction that this context is for."""
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

    def stop_interacting(self) -> None:
        """Stop receiving interactions for the linked menu."""
        self._stop_event.set()

    def extend_timeout(self, length: float) -> None:
        """
        Extend the menu's timeout by the given length.

        Args:
            length: The number of seconds to extend the timeout for.

        Returns:
            :obj:`None`
        """
        if self._timeout is None:
            return

        self._timeout.shift(length)

    def set_timeout(self, timeout: float) -> None:
        """
        Override the menu's timeout, resetting it to the given value.

        Args:
            timeout: The number of seconds to set the timeout for.

        Returns:
            :obj:`None`
        """
        if self._timeout is None:
            return

        self._timeout.update(asyncio.get_running_loop().time() + timeout)

    def selected_values_for(self, select: Select[T]) -> Sequence[T]:
        """
        Get the values the user selected for the given select menu.

        Args:
            select: The select menu component to get the selected values for.

        Returns:
            The selected values.
        """
        if self.interaction.custom_id != select.custom_id:
            return ()

        if isinstance(select, TextSelect):
            # This is **not** unreachable, pyright is just a silly sausage, and I don't want
            # to add an overload for all the supported select types :D
            return t.cast("Sequence[T]", self.interaction.values)

        resolved_data = self.interaction.resolved
        if resolved_data is None:
            raise RuntimeError("resolved option data is not available")

        resolved: list[T] = []
        for value in self.interaction.values:
            sf = hikari.Snowflake(value)
            resolved.append(
                resolved_data.members.get(sf)
                or resolved_data.users.get(sf)
                or resolved_data.roles.get(sf)
                or resolved_data.channels[sf]  # type: ignore[reportArgumentType]
            )

        return resolved

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

    async def respond(
        self,
        content: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
        *,
        ephemeral: bool = False,
        edit: bool = False,
        rebuild_menu: bool = False,
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
            rebuild_menu: Whether the menu this context is for should be rebuilt and sent with the response. This
                is just a convenience argument - passing `components=menu` will function the same way. If you **also**
                pass a value to ``components``, that value will be used instead.
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
        if rebuild_menu:
            components = components if components is not hikari.UNDEFINED else self.menu

        return await super().respond(
            content,
            ephemeral=ephemeral,
            edit=edit,
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


class MenuHandle:
    """
    Class encapsulating a single instance of an interaction listener for a component menu. Can be awaited in order
    to block until the menu completes.
    """

    __slots__ = ("__am", "_stop_event", "_task")

    def __init__(
        self,
        task: asyncio.Task[None] | None,
        stop_event: asyncio.Event,
        _am: _MenuInteractionHandlerContainer | None = None,
    ) -> None:
        self._task = task
        self._stop_event = stop_event

        self.__am: _MenuInteractionHandlerContainer | None = None

    @property
    def _am(self) -> _MenuInteractionHandlerContainer | None:
        return self.__am

    @_am.setter
    def _am(self, am: _MenuInteractionHandlerContainer) -> None:
        self.__am = am
        if self._stop_event.is_set():
            am._client._attached_menus.discard(am)

    async def wait(self) -> None:
        if self._task is None:
            await self._stop_event.wait()
            return

        await self._task

    def stop_interacting(self) -> None:
        """
        Stop the interaction listener that this handle represents.

        Returns:
            :obj:`None`
        """
        if self.__am is not None:
            self.__am._client._attached_menus.discard(self.__am)

        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()


class _MenuInteractionHandlerContainer:
    __slots__ = ("_client", "_ctx", "_menu", "_stop_event", "_tm", "custom_ids")

    def __init__(
        self,
        client: client_.Client,
        menu: Menu,
        tm: async_timeout.Timeout | None,
        stop_event: asyncio.Event,
        ctx: contextvars.Context | None,
    ) -> None:
        self._client = client
        self._menu = menu
        self._tm = tm
        self._stop_event = stop_event
        self._ctx = ctx

        self.custom_ids: dict[str, base.BaseComponent[special_endpoints.MessageActionRowBuilder]] = {
            c.custom_id: c for row in self._menu._rows for c in row if not isinstance(c, LinkButton)
        }

    async def on_interaction(
        self, interaction: hikari.ComponentInteraction, initial_response_sent: asyncio.Event
    ) -> None:
        context = MenuContext(
            client=self._client,
            menu=self._menu,
            interaction=interaction,
            component=self.custom_ids[interaction.custom_id],
            _timeout=self._tm,
            _stop_event=self._stop_event,
            _initial_response_sent=initial_response_sent,
        )

        token: contextvars.Token[linkd.Container | None] | None = None
        if self._ctx is not None:
            token = linkd.DI_CONTAINER.set(self._ctx.get(linkd.DI_CONTAINER))

        try:
            if not await self._menu.predicate(context):
                return

            callback: t.Callable[[MenuContext], t.Awaitable[None]] = getattr(context.component, "callback")
            await callback(context)
        finally:
            if token is not None:
                linkd.DI_CONTAINER.reset(token)

            if self._stop_event.is_set():
                self._client._attached_menus.discard(self)

        if self._stop_event.is_set():
            return

        if context._should_re_resolve_custom_ids:
            self.custom_ids = {c.custom_id: c for row in self._menu._rows for c in row if not isinstance(c, LinkButton)}


class Menu(base.BuildableComponentContainer[special_endpoints.MessageActionRowBuilder]):
    """Class representing a component menu."""

    __slots__ = ()

    _MAX_BUTTONS_PER_ROW: t.Final[int] = 5

    @property
    def _max_rows(self) -> int:
        return 5

    def _make_action_row(self) -> special_endpoints.MessageActionRowBuilder:
        return special_endpoints_impl.MessageActionRowBuilder()

    def _current_row_full(self) -> bool:
        return bool(
            len(self._rows[self._current_row]) >= self._MAX_BUTTONS_PER_ROW
            or ((r := self._rows[self._current_row]) and isinstance(r[0], Select))
        )

    def enable_all_components(self) -> t_ex.Self:
        """
        Utility function to set all components within this menu as enabled.

        Returns:
            The menu instance, for method chaining
        """
        for row in self._rows:
            for component in row:
                if hasattr(component, "disabled"):
                    setattr(component, "disabled", False)

        return self

    def disable_all_components(self) -> t_ex.Self:
        """
        Utility function to set all components within this menu as disabled.

        Returns:
            The menu instance, for method chaining.
        """
        for row in self._rows:
            for component in row:
                if hasattr(component, "disabled"):
                    setattr(component, "disabled", True)

        return self

    def add_interactive_button(
        self,
        style: hikari.ButtonStyle,
        on_press: ComponentCallback,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        label: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        emoji: hikari.UndefinedOr[hikari.Snowflakeish | str | hikari.Emoji] = hikari.UNDEFINED,
        disabled: bool = False,
    ) -> InteractiveButton:
        """
        Add an interactive button to this menu.

        Args:
            style: The style of the button.
            on_press: The asynchronous function to call when the button is pressed.
            custom_id: The custom ID for the button. Only specify this when you are creating a persistent
                menu. If unspecified, one will be generated for you.
            label: The label for the button.
            emoji: The emoji for the button.
            disabled: Whether the button is disabled.

        Returns:
            The created button.

        Raises:
            :obj:`ValueError`: When neither ``label`` nor ``emoji`` are specified.
        """
        if label is hikari.UNDEFINED and emoji is hikari.UNDEFINED:
            raise ValueError("at least one of 'label' and 'emoji' must be specified")

        return self.add(
            InteractiveButton(
                style=style,
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                label=label,
                emoji=emoji,
                disabled=disabled,
                callback=on_press,
            )
        )

    def add_link_button(
        self,
        url: str,
        *,
        label: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        emoji: hikari.UndefinedOr[hikari.Snowflakeish | str | hikari.Emoji] = hikari.UNDEFINED,
        disabled: bool = False,
    ) -> LinkButton:
        """
        Add a link button to this menu.

        Args:
            url: The url the button should link to.
            label: The label for the button.
            emoji: The emoji for the button.
            disabled: Whether the button is disabled.

        Returns:
            The created button.

        Raises:
            :obj:`ValueError`: When neither ``label`` nor ``emoji`` are specified.
        """
        if label is hikari.UNDEFINED and emoji is hikari.UNDEFINED:
            raise ValueError("at least one of 'label' and 'emoji' must be specified")

        return self.add(LinkButton(url=url, label=label, emoji=emoji, disabled=disabled))

    def add_text_select(
        self,
        options: ValidSelectOptions,
        on_select: ComponentCallback,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        placeholder: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> TextSelect:
        """
        Add a text select menu to this menu.

        Args:
            options: The options for the select menu.
            on_select: The asynchronous function to call when the select menu is submitted.
            custom_id: The custom ID for the select menu. Only specify this when you are creating a persistent
                menu. If unspecified, one will be generated for you.
            placeholder: The placeholder string for the select menu.
            min_values: The minimum number of values that can be selected.
            max_values: The maximum number of values that can be selected.
            disabled: Whether the select menu is disabled.

        Returns:
            The created select menu.
        """
        return self.add(
            TextSelect(
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                callback=on_select,
                options=options,
            )
        )

    def add_user_select(
        self,
        on_select: ComponentCallback,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        placeholder: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> UserSelect:
        """
        Add a user select menu to this menu.

        Args:
            on_select: The asynchronous function to call when the select menu is submitted.
            custom_id: The custom ID for the select menu. Only specify this when you are creating a persistent
                menu. If unspecified, one will be generated for you.
            placeholder: The placeholder string for the select menu.
            min_values: The minimum number of values that can be selected.
            max_values: The maximum number of values that can be selected.
            disabled: Whether the select menu is disabled.

        Returns:
            The created select menu.
        """
        return self.add(
            UserSelect(
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                callback=on_select,
            )
        )

    def add_role_select(
        self,
        on_select: ComponentCallback,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        placeholder: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> RoleSelect:
        """
        Add a role select menu to this menu.

        Args:
            on_select: The asynchronous function to call when the select menu is submitted.
            custom_id: The custom ID for the select menu. Only specify this when you are creating a persistent
                menu. If unspecified, one will be generated for you.
            placeholder: The placeholder string for the select menu.
            min_values: The minimum number of values that can be selected.
            max_values: The maximum number of values that can be selected.
            disabled: Whether the select menu is disabled.

        Returns:
            The created select menu.
        """
        return self.add(
            RoleSelect(
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                callback=on_select,
            )
        )

    def add_mentionable_select(
        self,
        on_select: ComponentCallback,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        placeholder: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> MentionableSelect:
        """
        Add a 'mentionable object' select menu to this menu.

        Args:
            on_select: The asynchronous function to call when the select menu is submitted.
            custom_id: The custom ID for the select menu. Only specify this when you are creating a persistent
                menu. If unspecified, one will be generated for you.
            placeholder: The placeholder string for the select menu.
            min_values: The minimum number of values that can be selected.
            max_values: The maximum number of values that can be selected.
            disabled: Whether the select menu is disabled.

        Returns:
            The created select menu.
        """
        return self.add(
            MentionableSelect(
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                callback=on_select,
            )
        )

    def add_channel_select(
        self,
        on_select: ComponentCallback,
        *,
        custom_id: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        placeholder: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]] = hikari.UNDEFINED,
    ) -> ChannelSelect:
        """
        Add a channel select menu to this menu.

        Args:
            on_select: The asynchronous function to call when the select menu is submitted.
            custom_id: The custom ID for the select menu. Only specify this when you are creating a persistent
                menu. If unspecified, one will be generated for you.
            placeholder: The placeholder string for the select menu.
            min_values: The minimum number of values that can be selected.
            max_values: The maximum number of values that can be selected.
            disabled: Whether the select menu is disabled.
            channel_types: The channel types allowed to be selected.

        Returns:
            The created select menu.
        """
        return self.add(
            ChannelSelect(
                custom_id=custom_id or f"lb_{uuid.uuid4()}",
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                callback=on_select,
                channel_types=channel_types,
            )
        )

    async def attach(self, client: client_.Client, *, timeout: float | None = 30) -> None:
        """
        Attach this menu to the given client, starting it - and wait for it to terminate. You may optionally
        provide a timeout, after which an :obj:`asyncio.TimeoutError` will be raised.

        If you wish to run the menu in the background, or wait on it later, you should use `.attach_persistent()`
        instead.

        Args:
            client: The client to attach the menu to.
            timeout: The amount of time in seconds before the menu will time out. Defaults to `30` seconds. Set to
                :obj:`None` to disable timeout.

        Returns:
            :obj:`None`

        Raises:
            :obj:`asyncio.TimeoutError`: If the timeout is exceeded.

        See Also:
            :meth:`~lightbulb.components.menus.Menu.attach_persistent`
        """
        stop_event, ctx = asyncio.Event(), contextvars.copy_context()

        stack = contextlib.AsyncExitStack()
        async with stack:
            tm = None
            if timeout is not None:
                tm = await stack.enter_async_context(async_timeout.timeout(timeout))

            am = _MenuInteractionHandlerContainer(client, self, tm, stop_event, ctx)
            client._attached_menus.add(am)

            try:
                await stop_event.wait()
            finally:
                client._attached_menus.discard(am)

    def attach_persistent(self, client: client_.Client, *, timeout: float | None = 30) -> MenuHandle:
        """
        Attach this menu to the given client, starting it in the background. You may optionally provide
        a timeout, after which an :obj:`asyncio.TimeoutError` will be raised within the created task. This method
        returns a proxy object allowing you to wait on menu termination, or stop the menu manually.

        Args:
            client: The client to attach the menu to.
            timeout: The amount of time in seconds before the menu will time out. Defaults to `30` seconds. Set to
                :obj:`None` to disable timeout.

        Returns:
            A proxy for the menu's interaction consumer. You can await `.wait()` on this in order
            to wait for the menu to terminate. You may also call `.stop_interacting()` to manually stop the menu.

        Note:
            If you wait on a menu to terminate that had ``timeout=None``, it is possible that it will block
            forever if the menu never terminates from within one of the component callbacks.
        """
        stop_event = asyncio.Event()

        if timeout is None:
            am = _MenuInteractionHandlerContainer(client, self, None, stop_event, None)
            client._attached_menus.add(am)
            return MenuHandle(None, stop_event, _am=am)

        handle = MenuHandle(None, stop_event)

        async def _run_with_timeout() -> None:
            async with async_timeout.timeout(timeout) as tm:
                am = _MenuInteractionHandlerContainer(client, self, tm, stop_event, None)
                handle._am = am
                client._attached_menus.add(am)

                try:
                    await stop_event.wait()
                finally:
                    client._attached_menus.discard(am)

        # Always suppress timeout exceptions from being logged to prevent clutter
        task = client.safe_create_task(_run_with_timeout())
        task.set_name(task.get_name() + "@notimeout")

        handle._task = task
        return handle

    async def predicate(self, ctx: MenuContext) -> bool:
        """
        The interaction predicate for this menu. This will be called **before** the appropriate
        component callback function is called, and should return a boolean indicating whether to
        continue and invoke the callback.

        You could use this to check that the correct user has pressed a button, has the correct
        permissions, or anything else you'd need to check before running component logic.

        By default, the implementation of this function always returns :obj:`True` and performs no logic.

        Args:
            ctx: The context for this component invocation.

        Returns:
            Boolean indicating whether the component callback function should be called.
        """
        return True
