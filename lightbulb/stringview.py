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

__all__: typing.Final[typing.List[str]] = ["StringView"]

import typing

from lightbulb import errors

_quotes = {
    '"': '"',
    "'": "'",
    "‘": "’",
    "‚": "‛",
    "“": "”",
    "„": "‟",
    "⹂": "⹂",
    "「": "」",
    "『": "』",
    "〝": "〞",
    "﹁": "﹂",
    "﹃": "﹄",
    "＂": "＂",
    "｢": "｣",
    "«": "»",
    "‹": "›",
    "《": "》",
    "〈": "〉",
}


class StringView:
    """
    Class to decompose a string (generally message content) into its arguments.

    Args:
        raw_string (:obj:`str`): The string to break down into its arguments.
    """

    def __init__(self, raw_string: str) -> None:
        self.text = raw_string
        self.index = 0
        self.final_args = []
        self.current_arg = []
        self.expect_quote = None

    def _next_str(self) -> str:
        buff = []
        while self.index < len(self.text):
            char = self.text[self.index]
            if char.isspace() and self.expect_quote is None:
                self.index += 1
                return "".join(buff)
            elif not self.expect_quote and char in _quotes:
                self.expect_quote = char
                self.index += 1
                continue
            elif char == self.expect_quote:
                self.expect_quote = None
                self.index += 1
                return "".join(buff)
            elif char == "\\":
                self.index += 1
                if self.index < len(self.text):
                    buff.append(self.text[self.index])
                    self.index += 1
                    continue
                raise errors.PrematureEOF()
            else:
                buff.append(char)
                self.index += 1

        if self.expect_quote:
            raise errors.UnclosedQuotes("".join(buff))
        if buff:
            return "".join(buff)

    def deconstruct_str(self, *, max_parse: typing.Optional[int] = None) -> typing.Tuple[typing.List[str], str]:
        """
        Method called to deconstruct the string passed in at instantiation into
        a list of all of its arguments. Arguments are defined as words separated by whitespace,
        or as words enclosed in quotation marks.

        Keyword Args:
            max_parse (Optional[ :obj:`int` ]): The maximum number of arguments to parse. If unspecified,
                as many arguments will be parsed as possible.

        Raises:
            :obj:`~.errors.UnclosedQuotes`: When an unexpected EOF is encountered.

        Returns:
            Tuple[ List[ :obj:`str` ], :obj:`str`]: The arguments extracted from the string, as well as any
                remainder if ``max_parse`` was supplied.
        """
        max_parse = max_parse if max_parse is not None else float("inf")

        finished = False
        args_list = []
        while not finished and len(args_list) < max_parse:
            arg = self._next_str()
            if arg is not None:
                args_list.append(arg)
            else:
                finished = True
        return args_list, self.text[self.index :].strip()
