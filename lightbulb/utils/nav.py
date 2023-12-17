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

import contextlib

__all__ = [
    "ReactionNavigator",
    "ButtonNavigator",
    "ReactionButton",
    "ComponentButton",
    "next_page",
    "prev_page",
    "first_page",
    "last_page",
    "stop",
]

import asyncio
import typing as t

import hikari
from hikari.components import ButtonStyle

if t.TYPE_CHECKING:
    from hikari.api.special_endpoints import MessageActionRowBuilder

    from lightbulb import context as context_


class ReactionButton:
    """
    A reaction-based navigator button. Contains the emoji linked to the button as well as
    the coroutine to be called when the button is pressed.

    Args:
        emoji (Union[:obj:`str`, :obj:`~hikari.emojis.Emoji`]): The emoji linked to the button.
        callback: The coroutine function to be called on button press.
    """

    __slots__ = ("emoji", "callback")

    def __init__(
        self,
        emoji: t.Union[str, hikari.Emoji],
        callback: t.Callable[[ReactionNavigator[T], hikari.ReactionAddEvent], t.Coroutine[t.Any, t.Any, None]],
    ) -> None:
        if isinstance(emoji, str):
            emoji = hikari.Emoji.parse(emoji)
        self.emoji = emoji
        self.callback = callback

    def is_pressed(self, event: hikari.ReactionAddEvent) -> bool:
        """
        Check if the button is pressed in a given event.

        Args:
            event (:obj:`~hikari.events.message.MessageReactionEvent`): The event to check the button is pressed in.

        Returns:
            :obj:`bool`: Whether the button is pressed in the given event.
        """
        if event.emoji_id is not None and isinstance(self.emoji, hikari.CustomEmoji):
            return event.emoji_id == self.emoji.id
        return event.emoji_name == self.emoji.name

    def press(self, nav: ReactionNavigator[T], event: hikari.ReactionAddEvent) -> t.Coroutine[t.Any, t.Any, None]:
        """
        Call the button's callback coroutine and return the awaitable.

        Returns:
            Coroutine[``None``, Any, ``None``]: Returned awaitable from the coroutine call.
        """
        return self.callback(nav, event)


class ComponentButton:
    """
    A component-based navigator button. Contains the custom_id linked to the button as well as
    the coroutine to be called when the button is pressed.

    Args:
        label (:obj:`str`): The label of the button.
        label_is_emoji (:obj:`bool`): Whether the label is an emoji or not. This affects whether ``set_label`` or
            ``set_emoji`` is called when building the button.
        style (:obj:`hikari.InteractiveButtonTypesT`): The style of the button.
        custom_id (:obj:`str`): The custom ID of the button.
        callback: The coroutine function to be called on button press.
    """

    __slots__ = ("custom_id", "callback", "label", "style", "label_is_emoji")

    def __init__(
        self,
        label: str,
        label_is_emoji: bool,
        style: hikari.InteractiveButtonTypesT,
        custom_id: str,
        callback: t.Callable[[ButtonNavigator[T], hikari.InteractionCreateEvent], t.Coroutine[t.Any, t.Any, None]],
    ) -> None:
        self.label = label
        self.label_is_emoji = label_is_emoji
        self.style = style
        self.custom_id = custom_id
        self.callback = callback

    def build(self, container: MessageActionRowBuilder, disabled: bool = False) -> None:
        """
        Build and add the button to the given container.

        Args:
            container (:obj:`hikari.api.special_endpoints.MessageActionRowBuilder`): The container to add the button to.
            disabled (:obj:`bool`): Whether to display the button as disabled.

        Returns:
            ``None``
        """
        container.add_interactive_button(
            self.style,
            self.custom_id,
            is_disabled=disabled,
            **{"emoji" if self.label_is_emoji else "label": self.label},
        )

    def is_pressed(self, event: hikari.InteractionCreateEvent) -> bool:
        """
        Check if the button is pressed in a given event.

        Args:
            event (:obj:`~hikari.InteractionCreateEvent`): The event to check the button is pressed in.

        Returns:
            :obj:`bool`: Whether or not the button is pressed in the given event.
        """
        assert isinstance(event.interaction, hikari.ComponentInteraction)
        return event.interaction.custom_id == self.custom_id

    def press(self, nav: ButtonNavigator[T], event: hikari.InteractionCreateEvent) -> t.Coroutine[t.Any, t.Any, None]:
        """
        Call the button's callback coroutine and return the awaitable.

        Returns:
            Coroutine[Any, Any, ``None``]: Returned awaitable from the coroutine call.
        """
        return self.callback(nav, event)


T = t.TypeVar("T")


async def next_page(nav: t.Union[ReactionNavigator[T], ButtonNavigator[T]], _: hikari.Event) -> None:
    """:obj:`NavButton` callback to make the ReactionNavigator go to the next page."""
    nav.current_page_index += 1
    nav.current_page_index %= len(nav.pages)


async def prev_page(nav: t.Union[ReactionNavigator[T], ButtonNavigator[T]], _: hikari.Event) -> None:
    """:obj:`NavButton` callback to make the navigator go to the previous page."""
    nav.current_page_index -= 1
    if nav.current_page_index < 0:
        nav.current_page_index = len(nav.pages) - 1


async def first_page(nav: t.Union[ReactionNavigator[T], ButtonNavigator[T]], _: hikari.Event) -> None:
    """:obj:`NavButton` callback to make the navigator go to the first page."""
    nav.current_page_index = 0


async def last_page(nav: t.Union[ReactionNavigator[T], ButtonNavigator[T]], _: hikari.Event) -> None:
    """:obj:`NavButton` callback to make the navigator go to the last page."""
    nav.current_page_index = len(nav.pages) - 1


async def stop(nav: t.Union[ReactionNavigator[T], ButtonNavigator[T]], _: hikari.Event) -> None:
    """:obj:`NavButton` callback to make the navigator stop navigation."""
    assert nav._msg is not None
    await nav._remove_listener()
    await nav._msg.delete()
    nav._msg = None
    if nav._timeout_task is not None:
        nav._timeout_task.cancel()


class ReactionNavigator(t.Generic[T]):
    r"""
    A reaction navigator system for navigating through a list of items that can be sent through the
    ``content`` argument of :obj:`hikari.Message.respond`.

    Default buttons:

    - ``\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}`` (Go to first page)
    - ``\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}`` (Go to previous page)
    - ``\N{BLACK SQUARE FOR STOP}\\N{VARIATION SELECTOR-16}`` (Stop navigation)
    - ``\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}`` (Go to next page)
    - ``\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}`` (Go to last page)

    Args:
        pages (Sequence[T]): Pages to navigate through.

    Keyword Args:
        buttons (Optional[Sequence[:obj:`~.utils.nav.NavButton`]]): Buttons to
            use the navigator with. Uses the default buttons if not specified.
        timeout (:obj:`float`): The navigator timeout in seconds. After the timeout has expired, navigator reactions
            will no longer work. Defaults to 120 (2 minutes).

    Example:
        .. code-block:: python

            from lightbulb.utils import pag, nav

            @bot.command()
            async def foo(ctx):
                paginated_help = pag.StringPaginator()
                for l in thing_that_creates_a_lot_of_text.split("\n"):
                    paginated_help.add_line(l)
                navigator = nav.ReactionNavigator(paginated_help.build_pages())
                await navigator.run(ctx)
    """

    __slots__ = ("pages", "buttons", "_timeout", "current_page_index", "_context", "_msg", "_timeout_task")

    def __init__(
        self,
        pages: t.Union[t.Iterable[T], t.Iterator[T]],
        *,
        buttons: t.Optional[t.Sequence[ReactionButton]] = None,
        timeout: float = 120,
    ) -> None:
        if not pages:
            raise ValueError("You cannot pass fewer than 1 page to the navigator.")
        self.pages: t.Sequence[T] = tuple(pages)

        if buttons is not None and any(not isinstance(btn, ReactionButton) for btn in buttons):
            raise TypeError("Buttons must be an instance of ReactionButton")

        self.buttons: t.Sequence[ReactionButton]
        if len(self.pages) == 1 and not buttons:
            self.buttons = [ReactionButton("\N{CROSS MARK}", stop)]
        else:
            self.buttons = buttons if buttons is not None else self.create_default_buttons()

        self._timeout: float = timeout
        self.current_page_index: int = 0
        self._context: t.Optional[context_.base.Context] = None
        self._msg: t.Optional[hikari.Message] = None
        self._timeout_task: t.Optional[asyncio.Task[None]] = None

    async def _edit_msg(self, message: hikari.Message, page: T) -> hikari.Message:
        return await message.edit(page)

    async def _send_initial_msg(self, page: T) -> hikari.Message:
        assert self._context is not None
        resp = await self._context.respond(page)
        return await resp.message()

    def create_default_buttons(self) -> t.List[ReactionButton]:
        buttons = [
            ReactionButton(
                "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}", first_page
            ),
            ReactionButton("\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", prev_page),
            ReactionButton("\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}", stop),
            ReactionButton("\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", next_page),
            ReactionButton(
                "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}", last_page
            ),
        ]
        return buttons

    async def _process_reaction_add(self, event: hikari.ReactionAddEvent) -> None:
        assert self._context is not None and self._msg is not None
        if event.user_id != self._context.author.id or event.message_id != self._msg.id:
            return

        for button in self.buttons:
            if button.is_pressed(event):
                await button.press(self, event)
                if self._msg is not None:
                    await self._edit_msg(self._msg, self.pages[self.current_page_index])

                    with contextlib.suppress(hikari.ForbiddenError):
                        await self._msg.remove_reaction(button.emoji, user=self._context.author)
                break

    async def _remove_listener(self) -> None:
        assert self._context is not None
        self._context.app.unsubscribe(hikari.ReactionAddEvent, self._process_reaction_add)

        if self._msg is None:
            return

        with contextlib.suppress(hikari.ForbiddenError, hikari.NotFoundError):
            await self._msg.delete()

    async def _timeout_coro(self) -> None:
        try:
            await asyncio.sleep(self._timeout)
            await self._remove_listener()
        except asyncio.CancelledError:
            pass

    async def run(self, context: context_.base.Context) -> None:
        """
        Run the navigator under the given context.

        Args:
            context (:obj:`~.context.base.Context`): Context
                to run the navigator under.

        Returns:
            ``None``

        Raises:
            :obj:`hikari.MissingIntentError`: If the bot does not have the relevant reaction intent(s) for
                the navigator to function.
        """
        intent_to_check_for = (
            hikari.Intents.GUILD_MESSAGE_REACTIONS
            if context.guild_id is not None
            else hikari.Intents.DM_MESSAGE_REACTIONS
        )
        if not (context.app.intents & intent_to_check_for) == intent_to_check_for:
            raise hikari.MissingIntentError(intent_to_check_for)

        self._context = context
        context.app.subscribe(hikari.ReactionAddEvent, self._process_reaction_add)
        self._msg = await self._send_initial_msg(self.pages[self.current_page_index])
        for emoji in [button.emoji for button in self.buttons]:
            await self._msg.add_reaction(emoji)

        if self._timeout_task is not None:
            self._timeout_task.cancel()
        self._timeout_task = asyncio.create_task(self._timeout_coro())


class ButtonNavigator(t.Generic[T]):
    r"""
    A button navigator system for navigating through a list of items that can be sent through the
    ``content`` argument of :obj:`hikari.Message.respond`.

    Args:
        pages (Sequence[T]): Pages to navigate through.

    Keyword Args:
        buttons (Sequence[:obj:`~ComponentButton`]): Buttons to
            use the navigator with. Uses the default buttons if not specified.
        timeout (:obj:`float`): The navigator timeout in seconds. After the timeout has expired, navigator buttons
            are disabled and will no longer work. Defaults to 120 (2 minutes).

    Example:
        .. code-block:: python

            from lightbulb.utils import pag, nav

            @bot.command()
            async def foo(ctx):
                paginated_help = pag.StringPaginator()
                for l in thing_that_creates_a_lot_of_text.split("\n"):
                    paginated_help.add_line(l)
                navigator = nav.ButtonNavigator(paginated_help.build_pages())
                await navigator.run(ctx)
    """

    __slots__ = ("pages", "buttons", "_timeout", "current_page_index", "_context", "_msg", "_timeout_task")

    def __init__(
        self,
        pages: t.Union[t.Iterable[T], t.Iterator[T]],
        *,
        buttons: t.Optional[t.Sequence[ComponentButton]] = None,
        timeout: float = 120,
    ) -> None:
        if not pages:
            raise ValueError("You cannot pass fewer than 1 page to the navigator.")
        self.pages: t.Sequence[T] = tuple(pages)

        self.buttons: t.Sequence[ComponentButton]
        if len(self.pages) == 1 and not buttons:
            self.buttons = [ComponentButton("\N{CROSS MARK}", True, ButtonStyle.DANGER, "stop", stop)]
        else:
            self.buttons = buttons if buttons is not None else self.create_default_buttons()

        self._timeout: float = timeout
        self.current_page_index: int = 0
        self._context: t.Optional[context_.base.Context] = None
        self._msg: t.Optional[hikari.Message] = None
        self._timeout_task: t.Optional[asyncio.Task[None]] = None

    async def _send_initial_msg(self, page: T) -> hikari.Message:
        assert self._context is not None
        buttons = await self.build_buttons()
        resp = await self._context.respond(page, component=buttons)
        return await resp.message()

    async def _edit_msg(self, inter: hikari.ComponentInteraction, page: T) -> None:
        buttons = await self.build_buttons(disabled=self._msg is None)
        try:
            await inter.create_initial_response(hikari.ResponseType.MESSAGE_UPDATE, page, component=buttons)
        except hikari.NotFoundError:
            await inter.edit_initial_response(page, component=buttons)

    def create_default_buttons(self) -> t.Sequence[ComponentButton]:
        buttons = [
            ComponentButton(
                "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                True,
                ButtonStyle.PRIMARY,
                "first_page",
                first_page,
            ),
            ComponentButton(
                "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
                True,
                ButtonStyle.PRIMARY,
                "prev_page",
                prev_page,
            ),
            ComponentButton(
                "\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}", True, ButtonStyle.DANGER, "stop", stop
            ),
            ComponentButton(
                "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
                True,
                ButtonStyle.PRIMARY,
                "next_page",
                next_page,
            ),
            ComponentButton(
                "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                True,
                ButtonStyle.PRIMARY,
                "last_page",
                last_page,
            ),
        ]
        return buttons

    async def build_buttons(self, disabled: bool = False) -> hikari.UndefinedOr[MessageActionRowBuilder]:
        assert self._context is not None
        buttons = self._context.app.rest.build_message_action_row()
        for button in self.buttons:
            button.build(buttons, disabled)
        return buttons

    async def _process_interaction_create(self, event: hikari.InteractionCreateEvent) -> None:
        if not isinstance(event.interaction, hikari.ComponentInteraction):
            return

        if self._msg is None:
            return

        assert self._context is not None

        if event.interaction.message.id != self._msg.id or event.interaction.user.id != self._context.author.id:
            return

        for button in self.buttons:
            if button.is_pressed(event):
                await button.press(self, event)
                if self._msg is not None:
                    await self._edit_msg(event.interaction, self.pages[self.current_page_index])
                break

    async def _remove_listener(self) -> None:
        assert self._context is not None
        self._context.app.unsubscribe(hikari.InteractionCreateEvent, self._process_interaction_create)

        if self._msg is not None:
            await self._msg.edit(component=await self.build_buttons(True))

    async def _timeout_coro(self) -> None:
        try:
            await asyncio.sleep(self._timeout)
            await self._remove_listener()
        except asyncio.CancelledError:
            pass

    async def run(self, context: context_.base.Context) -> None:
        """
        Run the navigator under the given context.

        Args:
            context (:obj:`~.context.base.Context`): Context
                to run the navigator under.

        Returns:
            ``None``
        """
        self._context = context
        context.app.subscribe(hikari.InteractionCreateEvent, self._process_interaction_create)
        self._msg = await self._send_initial_msg(self.pages[self.current_page_index])

        if self._timeout_task is not None:
            self._timeout_task.cancel()
        self._timeout_task = asyncio.create_task(self._timeout_coro())
