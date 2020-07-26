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

__all__: typing.Final[typing.List[str]] = ["StringPaginator", "EmbedPaginator", "Paginator"]

import abc
import io
import textwrap
import typing

from hikari import Embed


T = typing.TypeVar("T")


class Paginator(abc.ABC, typing.Generic[T]):
    @abc.abstractmethod
    def __init__(
        self,
        *,
        max_lines: typing.Optional[int] = None,
        max_chars: int = 2000,
        prefix: str = "",
        suffix: str = "",
        line_separator: str = "\n",
        page_factory: typing.Callable[[int, str], T] = lambda i, s: s,
    ) -> None:
        self._page_prefix: str = prefix
        self._page_suffix: str = suffix
        # Dummy minimum content size. This is never used, but is just symbolic for readability.
        min_content = f"A{line_separator}"

        # at least one line of content.
        extra_lines = prefix.count(line_separator) + suffix.count(line_separator)
        min_total_lines = min_content.count(line_separator) + extra_lines

        if max_lines is not None:
            if max_lines < min_total_lines:
                raise ValueError(f"This configuration requires at least {min_total_lines} lines per page!")

        # At least 1 character per page, or we recurse forever!
        prefix_len = len(prefix) + len(suffix)
        min_total_len = prefix_len + len(min_content)

        if max_chars < min_total_len:
            raise ValueError(f"This configuration requires at least {min_total_len} characters per page.")

        self._max_total_chars = max_chars
        self._max_total_lines = max_lines if max_lines is not None else float("inf")
        self._max_content_chars = max_chars - prefix_len
        self._max_content_lines = max_lines - extra_lines if max_lines is not None else float("inf")
        self._line_separator = line_separator
        self._next_page: io.StringIO = io.StringIO()
        self._pages: typing.List[str] = []
        self._page_factory = page_factory
        self.current_page: int = 0

    def build_pages(self, page_number_start: int = 1) -> typing.Iterator[T]:
        """
        The current pages that have been created.

        Args:
            page_number_start (:obj:`int`): The page number to start at.
                Defaults to ``1``.

        Returns:
            Iterator[ T ]: Lazy generator of each page.
        """
        # Only add the last page if it is not empty.
        if self._next_page.tell():
            last_page = self._next_page.getvalue()
            if len(last_page) > 0:
                self.new_page()

        for i, page in enumerate(self._pages, start=page_number_start):
            yield self._page_factory(i, page)

    def add_line(self, line: typing.Any) -> None:
        """
        Add a line to the paginator.

        Args:
            line (:obj:`typing.Any`): The line to add to the paginator.
                Will be converted to a :obj:`str`.

        Returns:
            ``None``
        """
        whole_text = str(line).replace("\t", (" " * 4)).replace("\r", "").split(self._line_separator)

        for line in whole_text:
            self._add_one_line(line)

    def _add_one_line(self, line: str) -> None:
        existing_chars, existing_lines = self._sizes()
        remaining_chars = self._max_content_chars - existing_chars
        remaining_lines = self._max_content_lines - existing_lines
        this_char_count = len(line)

        if not self._next_page.tell():
            self._next_page.write(self._page_prefix)

        if this_char_count > self._max_content_chars:
            self._chunk_add(line)
            return

        if remaining_chars < this_char_count or remaining_lines <= 0:
            self.new_page()
            self._add_one_line(line)
            return

        self._next_page.write(line)
        self._next_page.write(self._line_separator)

    def _chunk_add(self, line: str) -> None:
        # Try to split up words, if not, break mid-word.
        wrapper = textwrap.TextWrapper(
            width=self._max_content_chars, expand_tabs=True, tabsize=4, max_lines=self._max_content_lines,
        )

        lines = wrapper.wrap(line)

        for line in lines:
            if len(line) > self._max_content_chars - len(self._line_separator):
                for i in range(0, len(line), self._max_content_chars):
                    next_line = line[i : i + self._max_content_chars]
                    self.add_line(next_line)
            else:
                self.add_line(line)

    def new_page(self) -> None:
        """
        Start a new page.

        Returns:
            ``None``
        """
        # Remove final newline if it is there.
        next_page = self._next_page.getvalue()
        if next_page.endswith(self._line_separator):
            next_page = next_page[: -len(self._line_separator)]
        next_page += self._page_suffix

        # Append page
        self._pages.append(next_page)

        # Clear buffer
        self._next_page.seek(0, 0)
        self._next_page.truncate(0)

    def _sizes(self) -> typing.Tuple[int, int]:
        page = self._next_page.getvalue()[len(self._page_prefix) :]
        current_chars = len(page)
        current_lines = page.count(self._line_separator)
        return current_chars, current_lines


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

    def __init__(
        self,
        *,
        max_lines: typing.Optional[int] = None,
        max_chars: int = 2000,
        prefix: str = "",
        suffix: str = "",
        line_separator: str = "\n",
    ) -> None:
        super().__init__(
            max_lines=max_lines, max_chars=max_chars, prefix=prefix, suffix=suffix, line_separator=line_separator,
        )


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

    def __init__(
        self,
        *,
        max_lines: typing.Optional[int] = None,
        max_chars: int = 2048,
        prefix: str = "",
        suffix: str = "",
        line_separator: str = "\n",
    ) -> None:
        super().__init__(
            max_lines=max_lines,
            max_chars=max_chars,
            prefix=prefix,
            suffix=suffix,
            line_separator=line_separator,
            page_factory=lambda i, s: Embed(description=s).set_footer(text=f"Page {i}"),
        )

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
            self.set_embed_factory(func)
            return func

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
        self._page_factory = func
