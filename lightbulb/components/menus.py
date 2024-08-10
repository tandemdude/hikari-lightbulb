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
    "RoleSelect",
    "Select",
    "TextSelect",
    "UserSelect",
]

import abc
import asyncio
import dataclasses
import typing as t
import uuid
from collections.abc import Sequence

import async_timeout
import hikari
from hikari.api import special_endpoints
from hikari.impl import special_endpoints as special_endpoints_impl

from lightbulb import context
from lightbulb.components import base

if t.TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable

    import typing_extensions as t_ex

    from lightbulb import client as client_

    ValidSelectOptions: t.TypeAlias = t.Union[Sequence["TextSelectOption"], Sequence[str], Sequence[tuple[str, str]]]
    ComponentCallback: t.TypeAlias = Callable[["MenuContext"], Awaitable[None]]

T = t.TypeVar("T")
MessageComponentT = t.TypeVar("MessageComponentT", bound=base.BaseComponent[special_endpoints.MessageActionRowBuilder])

INITIAL_RESPONSE_IDENTIFIER: t.Final[int] = -1


@dataclasses.dataclass(slots=True, kw_only=True)
class InteractiveButton(base.BaseComponent[special_endpoints.MessageActionRowBuilder]):
    style: hikari.ButtonStyle
    custom_id: str
    label: hikari.UndefinedOr[str]
    emoji: hikari.UndefinedOr[hikari.Snowflakeish | str | hikari.Emoji]
    disabled: bool
    callback: ComponentCallback

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_interactive_button(
            self.style,  # type: ignore[reportArgumentType]
            self.custom_id,
            emoji=self.emoji,
            label=self.label,
            is_disabled=self.disabled,
        )


@dataclasses.dataclass(slots=True, kw_only=True)
class LinkButton(base.BaseComponent[special_endpoints.MessageActionRowBuilder]):
    url: str
    label: hikari.UndefinedOr[str]
    emoji: hikari.UndefinedOr[hikari.Snowflakeish | str | hikari.Emoji]
    disabled: bool

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


@dataclasses.dataclass(slots=True, kw_only=True)
class Select(t.Generic[T], base.BaseComponent[special_endpoints.MessageActionRowBuilder], abc.ABC):
    custom_id: str
    placeholder: hikari.UndefinedOr[str]
    min_values: int
    max_values: int
    disabled: bool
    callback: ComponentCallback


@dataclasses.dataclass(slots=True)
class TextSelectOption:
    label: str
    value: str
    description: hikari.UndefinedOr[str] = hikari.UNDEFINED
    emoji: hikari.UndefinedOr[hikari.Snowflakeish | str | hikari.Emoji] = hikari.UNDEFINED
    default: bool = False


@dataclasses.dataclass(slots=True, kw_only=True)
class TextSelect(Select[str]):
    options: ValidSelectOptions

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


@dataclasses.dataclass(slots=True, kw_only=True)
class UserSelect(Select[hikari.User]):
    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_select_menu(
            hikari.ComponentType.USER_SELECT_MENU,
            self.custom_id,
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


@dataclasses.dataclass(slots=True, kw_only=True)
class RoleSelect(Select[hikari.Role]):
    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_select_menu(
            hikari.ComponentType.ROLE_SELECT_MENU,
            self.custom_id,
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


@dataclasses.dataclass(slots=True, kw_only=True)
class MentionableSelect(Select[hikari.Snowflake]):
    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_select_menu(
            hikari.ComponentType.MENTIONABLE_SELECT_MENU,
            self.custom_id,
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


@dataclasses.dataclass(slots=True, kw_only=True)
class ChannelSelect(Select[hikari.PartialChannel]):
    channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]]

    def add_to_row(self, row: special_endpoints.MessageActionRowBuilder) -> special_endpoints.MessageActionRowBuilder:
        return row.add_channel_menu(
            self.custom_id,
            channel_types=self.channel_types or (),
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.disabled,
        )


@dataclasses.dataclass(slots=True, kw_only=True)
class MenuContext(context.MessageResponseMixin[hikari.ComponentInteraction]):
    menu: Menu
    interaction: hikari.ComponentInteraction
    component: base.BaseComponent[special_endpoints.MessageActionRowBuilder]

    _should_stop_menu: bool = dataclasses.field(init=False, default=False, repr=False)
    _should_re_resolve_custom_ids: bool = dataclasses.field(init=False, default=False, repr=False)

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
        self._should_stop_menu = True

    def selected_values_for(self, select: Select[T]) -> Sequence[T]:
        if self.interaction.custom_id != select.custom_id:
            return ()

        if isinstance(select, TextSelect):
            # This is **not** unreachable, pyright is just a silly sausage, and I don't want
            # to add an overload for all the supported select types :D
            return t.cast(Sequence[T], self.interaction.values)

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
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        if rebuild_menu:
            components = components if components is not hikari.UNDEFINED else self.menu

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
                return INITIAL_RESPONSE_IDENTIFIER
            else:
                if edit:
                    return (
                        await self.edit_response(
                            INITIAL_RESPONSE_IDENTIFIER,
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


class Menu(Sequence[special_endpoints.ComponentBuilder]):
    __slots__ = ("__current_row", "__rows")

    _MAX_ROWS: t.Final[int] = 5
    _MAX_BUTTONS_PER_ROW: t.Final[int] = 5

    __current_row: int
    __rows: list[list[base.BaseComponent[special_endpoints.MessageActionRowBuilder]]]

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

            bld = special_endpoints_impl.MessageActionRowBuilder()
            for component in row:
                bld = component.add_to_row(bld)
            built_rows.append(bld)
        return built_rows

    @property
    def _current_row(self) -> int:
        try:
            return self.__current_row
        except AttributeError:
            self.__current_row = 0
        return self.__current_row

    @property
    def _rows(self) -> list[list[base.BaseComponent[special_endpoints.MessageActionRowBuilder]]]:
        try:
            return self.__rows
        except AttributeError:
            self.__rows = [[] for _ in range(self._MAX_ROWS)]
        return self.__rows

    def _current_row_full(self) -> bool:
        return bool(
            len(self._rows[self._current_row]) >= self._MAX_BUTTONS_PER_ROW
            or ((r := self._rows[self._current_row]) and isinstance(r[0], Select))
        )

    def clear_rows(self) -> t_ex.Self:
        self._rows.clear()
        return self

    def next_row(self) -> t_ex.Self:
        if self._current_row + 1 >= self._MAX_ROWS:
            raise RuntimeError("the maximum number of rows has been reached")
        self.__current_row += 1
        return self

    def previous_row(self) -> t_ex.Self:
        self.__current_row = max(0, self.__current_row - 1)
        return self

    def add(self, component: MessageComponentT) -> MessageComponentT:
        if self._current_row_full():
            self.next_row()

        self._rows[self._current_row].append(component)
        return component

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
        return self.add(
            InteractiveButton(
                style=style,
                custom_id=custom_id or str(uuid.uuid4()),
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
        return self.add(
            TextSelect(
                custom_id=custom_id or str(uuid.uuid4()),
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
        return self.add(
            UserSelect(
                custom_id=custom_id or str(uuid.uuid4()),
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
        return self.add(
            RoleSelect(
                custom_id=custom_id or str(uuid.uuid4()),
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
        return self.add(
            MentionableSelect(
                custom_id=custom_id or str(uuid.uuid4()),
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
        return self.add(
            ChannelSelect(
                custom_id=custom_id or str(uuid.uuid4()),
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                callback=on_select,
                channel_types=channel_types,
            )
        )

    async def _run_menu(self, client: client_.Client, timeout: float | None = None) -> None:  # noqa: ASYNC109
        all_custom_ids: dict[str, base.BaseComponent[special_endpoints.MessageActionRowBuilder]] = {}
        re_resolve_custom_ids: bool = True

        queue: asyncio.Queue[hikari.ComponentInteraction] = asyncio.Queue()
        client._menu_queues.add(queue)
        try:
            stopped: bool = False
            async with async_timeout.timeout(timeout):
                while not stopped:
                    if re_resolve_custom_ids:
                        all_custom_ids = {
                            c.custom_id: c for row in self._rows for c in row if not isinstance(c, LinkButton)
                        }
                        re_resolve_custom_ids = False

                    interaction = await queue.get()
                    if interaction.custom_id not in all_custom_ids:
                        continue

                    component = all_custom_ids[interaction.custom_id]
                    context = MenuContext(menu=self, interaction=interaction, component=component)

                    callback: t.Callable[[MenuContext], t.Awaitable[None]] = getattr(component, "callback")
                    await callback(context)

                    stopped = context._should_stop_menu
                    re_resolve_custom_ids = context._should_re_resolve_custom_ids
        finally:
            # Unregister queue from client
            client._menu_queues.remove(queue)

    async def attach(
        self,
        client: client_.Client,
        *,
        wait: bool = False,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> asyncio.Task[None]:
        task = client._safe_create_task(self._run_menu(client, timeout))
        if wait:
            await task
            if (exc := task.exception()) is not None and not isinstance(exc, asyncio.CancelledError):
                raise exc
        return task
