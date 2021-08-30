# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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

__all__: typing.List[str] = [
    "StringNavigator",
    "EmbedNavigator",
    "Navigator",
    "NavButton",
    "next_page",
    "prev_page",
    "first_page",
    "last_page",
    "stop",
]

import abc
import asyncio
import typing

import hikari

from lightbulb.context import Context


class NavButton:
    """
    A navigator button. Contains the emoji linked to the button as well as
    the coroutine to be called when the button is pressed.

    Args:
        emoji (Union[ :obj:`str`, :obj:`~hikari.emojis.Emoji` ]): The emoji linked to the button.
        callback: The coroutine function to be called on button press.
    """

    __slots__ = ("emoji", "callback")

    def __init__(
        self,
        emoji: typing.Union[str, hikari.Emoji],
        callback: typing.Callable[[Navigator, hikari.ReactionAddEvent], typing.Coroutine[typing.Any, typing.Any, None]],
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
            :obj:`bool`: Whether or not the button is pressed in the given event.
        """
        if event.emoji_id is not None and isinstance(self.emoji, hikari.CustomEmoji):
            return event.emoji_id == self.emoji.id
        return event.emoji_name == self.emoji.name

    def press(self, nav: Navigator, event: hikari.ReactionAddEvent) -> typing.Coroutine[typing.Any, typing.Any, None]:
        """
        Call the button's callback coroutine and return the awaitable.

        Returns:
            Coroutine[``None``, Any, ``None``]: Returned awaitable from the coroutine call.
        """
        return self.callback(nav, event)


T = typing.TypeVar("T")


async def next_page(nav: Navigator, _) -> None:
    """
    :obj:`NavButton` callback to make the navigator go to the next page.
    """
    nav.current_page_index += 1
    nav.current_page_index %= len(nav.pages)


async def prev_page(nav: Navigator, _) -> None:
    """
    :obj:`NavButton` callback to make the navigator go to the previous page.
    """
    nav.current_page_index -= 1
    if nav.current_page_index < 0:
        nav.current_page_index = len(nav.pages) - 1


async def first_page(nav: Navigator, _) -> None:
    """
    :obj:`NavButton` callback to make the navigator go to the first page.
    """
    nav.current_page_index = 0


async def last_page(nav: Navigator, _) -> None:
    """
    :obj:`NavButton` callback to make the navigator go to the last page.
    """
    nav.current_page_index = len(nav.pages) - 1


async def stop(nav: Navigator, _) -> None:
    """
    :obj:`NavButton` callback to make the navigator stop navigation.
    """
    nav._msg.app.unsubscribe(hikari.ReactionAddEvent, nav._process_reaction_add)
    await nav._msg.delete()
    nav._msg = None


class Navigator(abc.ABC, typing.Generic[T]):
    def __init__(
        self,
        pages: typing.Union[typing.Iterable[T], typing.Iterator[T]],
        *,
        buttons: typing.Optional[typing.Sequence[NavButton]] = None,
        timeout: float = 120,
    ) -> None:
        if not pages:
            raise ValueError("You cannot pass fewer than 1 page to the navigator.")
        self.pages: typing.Sequence[T] = tuple(pages)

        if buttons is not None:
            if any(not isinstance(btn, NavButton) for btn in buttons):
                raise TypeError("Buttons must be an instance of NavButton")

        if len(self.pages) == 1 and not buttons:
            self.buttons = [NavButton("\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}", stop)]
        else:
            self.buttons: typing.Sequence[NavButton] = buttons if buttons is not None else self.create_default_buttons()

        self._timeout: float = timeout
        self.current_page_index: int = 0
        self._context: typing.Optional[Context] = None
        self._msg: typing.Optional[hikari.Message] = None
        self._timeout_task = None

    @abc.abstractmethod
    async def _edit_msg(self, message: hikari.Message, page: T) -> hikari.Message:
        ...

    @abc.abstractmethod
    async def _send_initial_msg(self, page: T) -> hikari.Message:
        ...

    def create_default_buttons(self) -> typing.Sequence[NavButton]:
        buttons = (
            NavButton("\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}", first_page),
            NavButton("\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", prev_page),
            NavButton("\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}", stop),
            NavButton("\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", next_page),
            NavButton("\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}", last_page),
        )
        return buttons

    async def _process_reaction_add(self, event: hikari.ReactionAddEvent) -> None:
        if (
            event.user_id != self._context.message.author.id
            or event.channel_id != self._context.channel_id
            or event.message_id != self._msg.id
        ):
            return

        for button in self.buttons:
            if button.is_pressed(event):
                await button.press(self, event)
                if self._msg is not None:
                    await self._edit_msg(self._msg, self.pages[self.current_page_index])
                    try:
                        await self._msg.remove_reaction(button.emoji, user=self._context.author)
                    except hikari.ForbiddenError:
                        pass
                break

    async def _remove_reaction_listener(self):
        self._context.bot.unsubscribe(hikari.ReactionAddEvent, self._process_reaction_add)
        try:
            await self._msg.remove_all_reactions()
        except (hikari.ForbiddenError, hikari.NotFoundError):
            pass

    async def _timeout_coro(self):
        try:
            await asyncio.sleep(self._timeout)
            await self._remove_reaction_listener()
        except asyncio.CancelledError:
            pass

    async def run(self, context: Context) -> None:
        """
        Run the navigator under the given context.

        Args:
            context (:obj:`~.context.Context`): Context to run the navigator under

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
        if not (context.bot.intents & intent_to_check_for) == intent_to_check_for:
            raise hikari.MissingIntentError(intent_to_check_for)

        self._context = context
        context.bot.subscribe(hikari.ReactionAddEvent, self._process_reaction_add)
        self._msg = await self._send_initial_msg(self.pages[self.current_page_index])
        for emoji in [button.emoji for button in self.buttons]:
            await self._msg.add_reaction(emoji)

        if self._timeout_task is not None:
            self._timeout_task.cancel()
        self._timeout_task = asyncio.create_task(self._timeout_coro())


class StringNavigator(Navigator[str]):
    """
    A reaction navigator system for navigating through a list of string messages.

    Default buttons:

    - ``\\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\\N{VARIATION SELECTOR-16}`` (Go to first page)

    - ``\\N{BLACK LEFT-POINTING TRIANGLE}\\N{VARIATION SELECTOR-16}`` (Go to previous page)

    - ``\\N{BLACK SQUARE FOR STOP}\\N{VARIATION SELECTOR-16}`` (Stop navigation)

    - ``\\N{BLACK RIGHT-POINTING TRIANGLE}\\N{VARIATION SELECTOR-16}`` (Go to next page)

    - ``\\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\\N{VARIATION SELECTOR-16}`` (Go to last page)

    Args:
        pages (Sequence[ :obj:`str` ]): Pages to navigate through.

    Keyword Args:
        buttons (Optional[ Sequence[ :obj:`~.utils.nav.NavButton` ] ]): Buttons to
            use the navigator with. Uses the default buttons if not specified.
        timeout (:obj:`float`): The navigator timeout in seconds. After the timeout has expired, navigator reactions
            will no longer work. Defaults to 120 (2 minutes).

    Example:

        .. code-block:: python

            from lightbulb.utils import pag, nav

            @bot.command()
            async def foo(ctx):
                paginated_help = pag.StringPaginator()
                for l in thing_that_creates_a_lot_of_text.split("\\n"):
                    paginated_help.add_line(l)
                navigator = nav.StringNavigator(paginated_help.build_pages())
                await navigator.run(ctx)

    """

    async def _edit_msg(self, message: hikari.Message, page: str) -> hikari.Message:
        return await message.edit(page)

    async def _send_initial_msg(self, page: str) -> hikari.Message:
        return await self._context.respond(page)


class EmbedNavigator(Navigator[hikari.Embed]):
    """
    A reaction navigator system for navigating through a list of embeds.

    Args:
        pages (Iterable[ :obj:`~hikari.embeds.Embed` ]): Pages to navigate through.

    Keyword Args:
        buttons (Optional[ Iterable[ :obj:`~.utils.nav.NavButton` ] ]): Buttons to
            use the navigator with. Uses the default buttons if not specified.
        timeout (:obj:`float`): The navigator timeout in seconds. After the timeout has expired, navigator reactions
            will no longer work. Defaults to 120 (2 minutes).

    Note:
        See :obj:`~.utils.nav.StringNavigator` for the default buttons supplied by the navigator.
    """

    async def _edit_msg(self, message: hikari.Message, page: hikari.Embed) -> hikari.Message:
        return await message.edit(embed=page)

    async def _send_initial_msg(self, page: hikari.Embed) -> hikari.Message:
        return await self._context.respond(embed=page)
