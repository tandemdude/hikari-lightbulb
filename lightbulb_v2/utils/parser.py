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
import re
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


def _get_arg_pattern() -> re.Pattern[str]:
    patterns = []
    for opening, closing in _quotes.items():
        patterns.append(f"{opening}(.*?){closing}")
    patterns.append("\S+")
    return re.compile(f"({'|'.join(patterns)})")


class BaseParser(abc.ABC):
    ctx: context_.prefix.PrefixContext

    @abc.abstractmethod
    async def inject_args_to_context(self, content: str | None) -> None:
        ...


class Parser(BaseParser):
    RE_PAT: t.Final[re.Pattern[str]] = _get_arg_pattern()

    def __init__(self, context: context_.prefix.PrefixContext):
        self.ctx = context

    @staticmethod
    def _iterator(content: str) -> t.Iterator[t.Tuple[str, int]]:
        idx = 0
        while match := Parser.RE_PAT.search(content[idx:]):
            idx += match.span()[-1]
            # yielding idx might be handy later for consume rest options
            # TODO: find a better pattern so that we don't need this list comp
            yield [x for x in match.groups() if x is not None][-1], idx

    async def inject_args_to_context(self, content: str | None = None) -> None:
        if content is None:
            message = self.ctx.event.message
            assert message.content is not None
            content = message.content[len(self.ctx.prefix) + len(self.ctx.invoked_with) :]

        raw_args = self._iterator(content)
        assert self.ctx.command is not None
        options = list(self.ctx.command.options.values())
        while options:
            option = options.pop(0)
            _LOGGER.debug("Getting arg for %s with type %s", option.name, option.arg_type)
            try:
                raw_arg, _ = next(raw_args)  # we don't care about the idx for now
                _LOGGER.debug("Got raw arg %s", raw_arg)
            except StopIteration:
                _LOGGER.debug("Arguments have exhausted")
                if option.default is UNDEFINED and not option.required:
                    raise RuntimeError  # TODO: raise missing argument error

                self.ctx._options[option.name] = option.default
            else:
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
            if option.default is not UNDEFINED:
                self.ctx._options[option.name] = option.default
                _LOGGER.debug("Option has a default value, shifting to the next parameter")
                return False

            raise RuntimeError  # TODO: raise conversion failed error
        else:
            _LOGGER.debug("Sucessfuly converted %s to %s", raw, arg)
            self.ctx._options[option.name] = arg
            return True

    @staticmethod
    async def _convert(
        value: str,
        callback_or_type: t.Union[t.Callable[[str], T], t.Type[BaseConverter[T]]],
    ) -> T:
        if issubclass(callback_or_type, BaseConverter):
            raise NotImplementedError  # TODO: make use of maybe_await on convert method

        return callback_or_type(value)
