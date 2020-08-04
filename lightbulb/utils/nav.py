# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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

__all__: typing.List[str] = ["StringNavigator", "EmbedNavigator", "Navigator"]

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
        emoji (Union[ :obj:`str`, :obj:`~hikari.models.emojis.Emoji` ]): The emoji linked to the button.
        callback: The coroutine function to be called on button press.
    """

    __slots__ = ("emoji", "callback")

    def __init__(
        self,
        emoji: typing.Union[str, hikari.models.emojis.Emoji],
        callback: typing.Callable[[hikari.ReactionAddEvent], typing.Coroutine[typing.Any, typing.Any, None],],
    ) -> None:
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
        return str(event.emoji) == str(self.emoji)

    def press(self, event: hikari.ReactionAddEvent) -> typing.Coroutine[typing.Any, typing.Any, None]:
        """
        Call the button's callback coroutine and return the awaitable.

        Returns:
            Coroutine[``None``, Any, ``None``]: Returned awaitable from the coroutine call.
        """
        return self.callback(event)


T = typing.TypeVar("T")


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

        if len(self.pages) == 1 and not buttons:
            self.buttons = [NavButton("\N{BLACK SQUARE FOR STOP}", self._stop)]
        else:
            self.buttons: typing.Sequence[NavButton] = buttons if buttons is not None else self.create_default_buttons()

        self._timeout: float = timeout
        self.current_page_index: int = 0
        self._context: typing.Optional[Context] = None
        self._msg: typing.Optional[hikari.models.messages.Message] = None
        self._timeout_task = None

    @abc.abstractmethod
    async def _edit_msg(self, message: hikari.models.messages.Message, page: T) -> hikari.Message:
        ...

    @abc.abstractmethod
    async def _send_initial_msg(self, page: T) -> hikari.Message:
        ...

    def create_default_buttons(self) -> typing.Sequence[NavButton]:
        buttons = (
            NavButton("\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", self._first),
            NavButton("\N{BLACK LEFT-POINTING TRIANGLE}", self._prev),
            NavButton("\N{BLACK SQUARE FOR STOP}", self._stop),
            NavButton("\N{BLACK RIGHT-POINTING TRIANGLE}", self._next),
            NavButton("\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", self._last),
        )
        return buttons

    async def _next(self, _) -> None:
        self.current_page_index += 1
        self.current_page_index %= len(self.pages)

    async def _prev(self, _) -> None:
        self.current_page_index -= 1
        if self.current_page_index < 0:
            self.current_page_index = len(self.pages) - 1

    async def _first(self, _) -> None:
        self.current_page_index = 0

    async def _last(self, _) -> None:
        self.current_page_index = len(self.pages) - 1

    async def _stop(self, _) -> None:
        self._msg.app.event_dispatcher.unsubscribe(
            hikari.events.message.MessageReactionAddEvent, self._process_reaction_add
        )
        await self._msg.delete()
        self._msg = None

    async def _process_reaction_add(self, event: hikari.ReactionAddEvent) -> None:
        if (
            event.user_id != self._context.message.author.id
            or event.channel_id != self._context.channel_id
            or event.message_id != self._msg.id
        ):
            return

        for button in self.buttons:
            if button.is_pressed(event):
                await button.press(event)
                if self._msg is not None:
                    await self._edit_msg(self._msg, self.pages[self.current_page_index])
                    try:
                        await self._msg.remove_reaction(button.emoji, user=self._context.author)
                    except hikari.errors.Forbidden:
                        pass
                break

    async def _remove_reaction_listener(self):
        self._context.bot.event_dispatcher.unsubscribe(hikari.ReactionAddEvent, self._process_reaction_add)
        try:
            await self._msg.remove_all_reactions()
        except hikari.errors.Forbidden:
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
        """
        intent_to_check_for = (
            hikari.Intent.GUILD_MESSAGE_REACTIONS
            if context.guild_id is not None
            else hikari.Intent.PRIVATE_MESSAGE_REACTIONS
        )
        if not (context.bot._intents & intent_to_check_for) == intent_to_check_for:
            # TODO - raise more meaningful error and give it the missing intent.
            raise hikari.MissingIntentError(intent_to_check_for)

        self._context = context
        context.bot.event_dispatcher.subscribe(hikari.ReactionAddEvent, self._process_reaction_add)
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

    - ``\\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}`` (Go to first page)

    - ``\\N{BLACK LEFT-POINTING TRIANGLE}`` (Go to previous page)

    - ``\\N{BLACK SQUARE FOR STOP}`` (Stop navigation)

    - ``\\N{BLACK RIGHT-POINTING TRIANGLE}`` (Go to next page)

    - ``\\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}`` (Go to last page)

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
                navigator = nav.StringNavigator(paginated_help.pages)
                await navigator.run(ctx)

    """

    async def _edit_msg(self, message: hikari.models.messages.Message, page: str) -> hikari.Message:
        return await message.edit(page)

    async def _send_initial_msg(self, page: str) -> hikari.Message:
        return await self._context.reply(page)


class EmbedNavigator(Navigator[hikari.models.embeds.Embed]):
    """
    A reaction navigator system for navigating through a list of embeds.

    Args:
        pages (Iterable[ :obj:`~hikari.models.embeds.Embed` ]): Pages to navigate through.

    Keyword Args:
        buttons (Optional[ Iterable[ :obj:`~.utils.nav.NavButton` ] ]): Buttons to
            use the navigator with. Uses the default buttons if not specified.
        timeout (:obj:`float`): The navigator timeout in seconds. After the timeout has expired, navigator reactions
            will no longer work. Defaults to 120 (2 minutes).

    Note:
        See :obj:`~.utils.nav.StringNavigator` for the default buttons supplied by the navigator.
    """

    async def _edit_msg(
        self, message: hikari.models.messages.Message, page: hikari.models.embeds.Embed
    ) -> hikari.Message:
        return await message.edit(embed=page)

    async def _send_initial_msg(self, page: hikari.models.embeds.Embed) -> hikari.Message:
        return await self._context.reply(embed=page)
