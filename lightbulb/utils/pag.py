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
import typing
import abc

from hikari import Embed


T = typing.TypeVar("T")


class Paginator(abc.ABC, typing.Generic[T]):
    def __init__(
        self, *, max_lines: typing.Optional[int] = None, max_chars: int = 2000, prefix: str = "", suffix: str = ""
    ) -> None:
        self._page_prefix: str = prefix
        self._page_suffix: str = suffix
        self._max_lines: typing.Optional[int] = max_lines
        self._max_chars: int = max_chars
        self.current_page: int = 0
        self._next_page: typing.List[str] = []
        self._pages: typing.List[T] = []

    @property
    def pages(self) -> typing.Sequence[T]:
        """
        The current pages that have been created.

        Returns:
            Sequence[ T ]: Sequence of created pages.
        """
        return [*self._pages, self._get_complete_page(self._next_page)]

    @abc.abstractmethod
    def _get_complete_page(self, page: typing.List[str]) -> T:
        ...

    def add_line(self, line: str) -> None:
        """
        Add a line to the paginator.

        Args:
            line (:obj:`str`): The line to add to the paginator

        Returns:
            ``None``
        """
        if not self._next_page:
            self._next_page.append(self._page_prefix)

        exceeds_max_lines = (len(self._next_page) > self._max_lines) if self._max_lines is not None else False
        # Add 2 at the end to account for the extra \n chars once the page has been joined
        exceeds_max_chars = (len("\n".join(self._next_page)) + len(line) + len(self._page_suffix) + 2) > self._max_chars

        if exceeds_max_chars or exceeds_max_lines:
            self._pages.append(self._get_complete_page(self._next_page))
            self._next_page = []
            self.add_line(line)
        else:
            self._next_page.append(line)


class StringPaginator(Paginator[str]):
    """
    Creates pages from lines of text according to the given parameters.

    Text should be added to the paginator using :meth:`~.utils.pag.StringPaginator.add_line`, which
    will then be split up into an appropriate number of pages, accessible
    through :attr:`~.utils.pag.StringPaginator.pages`.

    Keyword Args:
        max_lines (Optional[ :obj:`int` ]): The maximum number of lines per page. Defaults to ``None``, meaning
            pages will use the ``max_chars`` param instead.
        max_chars (:obj:`int`): The maximum number of characters per page. Defaults to ``2000``, the max character
            limit for a discord message.
        prefix (:obj:`str`): The string to prefix every page with. Defaults to an empty string.
        suffix (:obj:`str`): The string to suffix every page with. Defaults to an empty string.

    Example:
        An example command using pagination to display all the guilds the bot is in.

        .. code-block:: python

            from lightbulb.utils.pag import StringPaginator

            @bot.command()
            async def guilds(ctx):
                guilds = await bot.rest.fetch_my_guilds()

                pag = StringPaginator(max_lines=10)
                for n, guild in enumerate(guilds, start=1):
                    pag.add_line(f"**{n}.** {guild.name}")
                for page in pag.pages:
                    await ctx.reply(page)
    """

    def _get_complete_page(self, page: typing.List[str]) -> str:
        return "\n".join([*page, self._page_suffix])


class EmbedPaginator(Paginator[Embed]):
    """
    Creates embed pages from lines of text according to the given parameters.

    Text is added to the paginator the same way as :obj:`~.utils.pag.StringPaginator`. The paginated text will
    be run though the defined :meth:`embed_factory`, or if no embed factory is defined
    then it will be inserted into the description of a default embed.

    Keyword Args:
        max_lines (Optional[ :obj:`int` ]): The maximum number of lines per page. Defaults to ``None``, meaning
            pages will use the ``max_chars`` param instead.
        max_chars (:obj:`int`): The maximum number of characters per page. Defaults to ``2048``, the max character
            limit for a discord message.
        prefix (:obj:`str`): The string to prefix every page with. Defaults to an empty string.
        suffix (:obj:`str`): The string to suffix every page with. Defaults to an empty string.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._embed_factory = lambda _, page: Embed(description=page)

    def embed_factory(self):
        """
        A decorator to mark a function as the paginator's embed factory. The page index and page content
        will be passed to the function when a new page is to be created.

        Example:
            The following code will give each embed created a random colour.

            .. code-block:: python

                from random import randint

                from lightbulb.utils.pag import EmbedPaginator
                from hikari import Embed

                pag = EmbedPaginator()

                @pag.embed_factory()
                def build_embed(page_index, page_content):
                    return Embed(description=page_content, colour=randint(0, 0xFFFFFF)

        See Also:
            :meth:`set_embed_factory`
        """

        def decorate(func):
            self._embed_factory = func

        return decorate

    def set_embed_factory(self, func: typing.Callable[[int, str], Embed]) -> None:
        """
        Method to set a callable as the paginator's embed factory. Alternative to :meth:`embed_factory`.

        Args:
            func (Callable[ [ :obj:`int`, :obj:`str` ], :obj:`~hikari.models.embeds.Embed` ]): The callable to
                set as the paginator's embed factory.

        Returns:
            ``None``

        See Also:
            :meth:`embed_factory`
        """
        self._embed_factory = func

    def _get_complete_page(self, page: typing.List[str]) -> Embed:
        return self._embed_factory(len(self._pages), "\n".join([*page, self._page_suffix]))
