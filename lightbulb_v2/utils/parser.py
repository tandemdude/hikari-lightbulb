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

__all__ = ["BaseParser", "Parser"]

import abc
import logging
import typing as t

from lightbulb_v2 import commands
from lightbulb_v2 import context as context_
from lightbulb_v2.commands.base import OptionModifier
from lightbulb_v2.converters.base import BaseConverter

T = t.TypeVar("T")
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
    __slots__ = ("ctx", "_idx", "buffer", "n", "prev", "options")

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
        self.options = list(context.command.options.values()) if context.command else []

    @property
    def is_eof(self) -> bool:
        return self.idx >= self.n

    @property
    def idx(self) -> int:
        return self._idx

    @idx.setter
    def idx(self, val: int) -> None:
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

    def get_previous(self) -> str | None:
        return None if self.idx == 0 else self.buffer[self.idx - 1]

    def get_word(self) -> str:
        """Gets the next word, will return an empty strig if EOF."""
        self.skip_ws()
        prev = self.idx
        while (char := self.get_char()) is not None and not char.isspace():
            pass
        self.prev = prev
        return self.buffer[prev : self.idx]

    def get_quoted_word(self) -> str:
        self.skip_ws()
        prev = self.idx
        if (closing := _quotes.get(t.cast(str, self.get_current()))) is None:
            return self.get_word()

        while (char := self.get_char()) is not None:
            if char == closing and self.get_previous() != "\\":
                break
        else:
            # EOF
            raise RuntimeError("expected a closing quote")  # TODO: raise proper error

        if (current := self.get_char()) is not None and not current.isspace():
            raise RuntimeError("expected a space after the closing quote")  # TODO: raise proper error

        self.prev = prev
        return self.buffer[prev + 1 : self.idx - 1].replace(f"\\{closing}", closing)

    def read_rest(self) -> str:
        self.idx = self.n
        return self.buffer[self.prev :]

    def get_option(self) -> commands.base.OptionLike | None:
        if self.options:
            return self.options.pop(0)

        return None

    async def inject_args_to_context(self) -> None:
        while option := self.get_option():
            _LOGGER.debug("Getting arg for %s with type %s", option.name, option.arg_type)

            if not (
                raw_arg := self.read_rest()
                if option.modifier is OptionModifier.CONSUME_REST
                else self.get_quoted_word()
            ):
                _LOGGER.debug("Arguments have exhausted")
                if option.required:
                    raise RuntimeError  # TODO: raise missing argument error

                self.ctx._options[option.name] = option.default

            _LOGGER.debug("Got raw arg %s", raw_arg)
            convert = self._greedy_convert if option.modifier is OptionModifier.GREEDY else self._try_convert
            await convert(raw_arg, option)

        # TODO: raise TooManyArguments?

    async def _try_convert(self, raw: str, option: commands.base.OptionLike) -> None:
        try:
            arg = await self._convert(raw, option.arg_type)
        except Exception as e:
            _LOGGER.debug("Failed to convert", exc_info=e)
            if option.required:
                raise RuntimeError  # TODO: raise conversion failed error

            self.ctx._options[option.name] = option.default
            _LOGGER.debug("Option has a default value, shifting to the next parameter")
            self.undo()
        else:
            _LOGGER.debug("Sucessfuly converted %s to %s", raw, arg)
            self.ctx._options[option.name] = arg

    async def _greedy_convert(self, raw: str, option: commands.base.OptionLike) -> None:
        self.ctx._options[option.name] = args = []
        _LOGGER.debug("Attempting to greedy convert %s to %s", raw, option.arg_type)
        while raw:
            try:
                arg = await self._convert(raw, option.arg_type)
            except Exception as e:
                _LOGGER.debug("Done greedy converting", exc_info=e)
                self.undo()
                break
            else:
                _LOGGER.debug("Appending %s", arg)
                args.append(arg)
                raw = self.get_quoted_word()

    async def _convert(
        self,
        value: str,
        callback_or_type: t.Union[t.Callable[[str], T], t.Type[BaseConverter[T]]],
    ) -> T:
        _LOGGER.debug("Attempting to convert %s to %s", value, callback_or_type)
        if issubclass(callback_or_type, BaseConverter):
            raise NotImplementedError  # TODO: make use of maybe_await on convert method

        return callback_or_type(value)
