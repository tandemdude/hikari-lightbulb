# -*- coding: utf-8 -*-
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

import abc
import logging
import typing as t

from hikari.undefined import UNDEFINED

from lightbulb_v2 import commands
from lightbulb_v2 import context as context_
from lightbulb_v2.converters.base import BaseConverter

T = t.TypeVar("T")
__all__ = ["BaseParser", "Parser"]
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
_LOGGER = logging.getLogger("lightbulb_v2.utils.parser")


class BaseParser(abc.ABC):
    ctx: context_.prefix.PrefixContext

    @abc.abstractmethod
    async def inject_args_to_context(self) -> None:
        ...


class Parser(BaseParser):
    __slots__ = ("ctx", "_idx", "buffer", "n", "prev")

    def __init__(self, context: context_.prefix.PrefixContext, buffer: str | None):
        self.ctx = context
        self._idx = 0

        if buffer is None:
            message = self.ctx.event.message
            assert message.content is not None
            buffer = message.content
            self._idx += len(self.ctx.prefix) + len(self.ctx.invoked_with)

        self.buffer = buffer
        self.n = len(buffer)
        self.prev = 0

    @property
    def is_eof(self) -> bool:
        return self.idx >= self.n

    @property
    def idx(self) -> int:
        return self._idx

    @idx.setter
    def idx(self, val: int) -> int:
        self.prev = self._idx
        self._idx = val

    def undo(self) -> None:
        self.idx = self.prev
        return None

    def skip_ws(self) -> None:
        prev = self.idx
        if (char := self.get_current()) is not None and not char.isspace():
            return None
        while (char := self.get_char()) is not None and char.isspace():
            pass
        self.prev = prev

    def get_char(self) -> str | None:
        self.idx += 1
        return self.get_current()

    def get_current(self) -> str | None:
        return None if self.is_eof else self.buffer[self.idx]

    def get_word(self) -> str:
        """Gets the next word, will return an empty strig if EOF."""
        self.skip_ws()
        prev = self.idx
        while (char := self.get_char()) is not None and not char.isspace():
            pass
        self.prev = prev
        return self.buffer[prev : self.idx]

    def get_quoted_word(self) -> str | None:
        self.skip_ws()
        prev = self.idx
        print(self.idx, self.get_current())
        if (closing := _quotes.get(self.get_current())) is None:
            return self.get_word()

        while (char := self.get_char()) is not None:
            if char == closing:
                break
        else:
            # EOF
            raise RuntimeError("expected a closing quote")  # TODO: raise proper error

        if (current := self.get_char()) is not None and not current.isspace():
            raise RuntimeError("expected a space after the closing quote")  # TODO: raise proper error

        self.prev = prev
        return self.buffer[prev + 1 : self.idx - 1]

    def read_rest(self) -> str:
        return self.buffer[self.idx : self.n]

    def _iterator(self) -> t.Iterator[t.Tuple[str, int]]:
        while word := self.get_quoted_word():
            yield word

    async def inject_args_to_context(self) -> None:
        raw_args = self._iterator()
        assert self.ctx.command is not None
        options = list(self.ctx.command.options.values())
        while options:
            option = options.pop(0)
            _LOGGER.debug("Getting arg for %s with type %s", option.name, option.arg_type)
            try:
                raw_arg = next(raw_args)
            except StopIteration:
                _LOGGER.debug("Arguments have exhausted")
                if option.required:
                    raise RuntimeError  # TODO: raise missing argument error

                self.ctx._options[option.name] = option.default
            else:
                _LOGGER.debug("Got raw arg %s", raw_arg)
                while 1:
                    if await self._try_convert(raw_arg, option) or not options:
                        break

                    option = options.pop(0)

    async def _try_convert(self, raw: str, option: commands.base.OptionLike) -> bool:
        try:
            _LOGGER.debug("Trying to convert %s to %s", raw, option.arg_type)
            arg = await self._convert(raw, option.arg_type)
        except Exception as e:
            _LOGGER.debug("Failed to convert", exc_info=e)
            if not option.required:
                self.ctx._options[option.name] = option.default
                _LOGGER.debug("Option has a default value, shifting to the next parameter")
                return False

            raise RuntimeError  # TODO: raise conversion failed error
        else:
            _LOGGER.debug("Sucessfuly converted %s to %s", raw, arg)
            self.ctx._options[option.name] = arg
            return True

    async def _greedy_convert(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        raise NotImplementedError

    @staticmethod
    async def _convert(
        value: str,
        callback_or_type: t.Union[t.Callable[[str], T], t.Type[BaseConverter[T]]],
    ) -> T:
        if issubclass(callback_or_type, BaseConverter):
            raise NotImplementedError  # TODO: make use of maybe_await on convert method

        return callback_or_type(value)
