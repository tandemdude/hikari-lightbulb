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

__all__ = ["BaseParser", "Parser"]

import abc
import inspect
import logging
import typing as t

import hikari

from lightbulb import commands
from lightbulb import context as context_
from lightbulb import errors
from lightbulb.commands.base import OptionLike
from lightbulb.commands.base import OptionModifier
from lightbulb.converters import CONVERTER_TYPE_MAPPING
from lightbulb.converters import BaseConverter

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
_LOGGER = logging.getLogger("lightbulb.utils.parser")


class BaseParser(abc.ABC):
    __slots__ = ("ctx", "_buffer", "len", "options")

    len: int
    ctx: context_.base.Context
    _buffer: str
    options: t.List[OptionLike]

    def __init__(
        self,
        context: context_.base.Context,
        buffer: t.Optional[str] = None,
        options: t.Optional[t.List[OptionLike]] = None,
    ) -> None:
        self.ctx = context

        if buffer is None:
            if not isinstance(self.ctx, context_.prefix.PrefixContext):
                raise RuntimeError("Please provide the buffer to parse")  # todo: proper error

            message = self.ctx.event.message
            assert message.content is not None
            buffer = message.content[len(self.ctx.prefix) + len(self.ctx.invoked_with) :]

        self.buffer = buffer

        if options is not None:
            self.options = options
        else:
            self.options = list(self.ctx.command.options.values()) if self.ctx.command else []

    @property
    def buffer(self) -> str:
        return self._buffer

    @buffer.setter
    def buffer(self, val: str) -> None:
        self._buffer = val
        self.len = len(val)

    @abc.abstractmethod
    async def parse(self) -> t.Dict[str, t.Any]:
        ...


class Parser(BaseParser):
    __slots__ = ("_idx", "prev")

    def __init__(
        self,
        context: context_.base.Context,
        buffer: t.Optional[str] = None,
        options: t.Optional[t.List[OptionLike]] = None,
    ) -> None:
        self._idx = 0
        self.prev = 0
        super().__init__(context, buffer, options)

    @property
    def is_eof(self) -> bool:
        return self.idx >= self.len

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

    def get_char(self) -> t.Optional[str]:
        self.idx += 1
        return self.get_current()

    def get_current(self) -> t.Optional[str]:
        return None if self.is_eof else self.buffer[self.idx]

    def get_previous(self) -> t.Optional[str]:
        return None if self.idx == 0 else self.buffer[self.idx - 1]

    def get_word(self) -> str:
        """Gets the next word, will return an empty string if EOF."""
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
        self.skip_ws()
        self.idx = self.len
        return self.buffer[self.prev :]

    def get_option(self) -> t.Optional[commands.base.OptionLike]:
        if self.options:
            return self.options.pop(0)

        return None

    async def parse(self) -> t.Dict[str, t.Any]:
        ret = {}
        attachments = list(self.ctx.attachments) if isinstance(self.ctx, context_.prefix.PrefixContext) else []
        while option := self.get_option():
            if option.arg_type in (hikari.OptionType.ATTACHMENT, hikari.Attachment):
                if not attachments:
                    if not option.required:
                        ret[option.name] = option.default
                        continue
                    raise errors.MissingRequiredAttachmentArgument(
                        "Command invocation expects an attachment but none were found.", missing=option
                    )
                ret[option.name] = attachments.pop(0)
                continue

            _LOGGER.debug("Getting arg for %s with type %s", option.name, option.arg_type)

            if not (
                raw_arg := self.read_rest()
                if option.modifier is OptionModifier.CONSUME_REST
                else self.get_quoted_word()
            ):
                _LOGGER.debug("Arguments have exhausted")
                if option.required:
                    raise errors.NotEnoughArguments(
                        "Command invocation is missing one or more required arguments.",
                        missing=[option, *(o for o in self.options if o.required)],
                    )

                ret[option.name] = option.default
                continue

            _LOGGER.debug("Got raw arg %s", raw_arg)
            convert = self._greedy_convert if option.modifier is OptionModifier.GREEDY else self._try_convert
            await convert(raw_arg, option, ret)
            self._validate(option, ret[option.name])
        return ret

    async def _try_convert(self, raw: str, option: commands.base.OptionLike, out: t.Dict[str, t.Any]) -> None:
        try:
            arg = await self._convert(raw, option.arg_type)
        except Exception as e:
            _LOGGER.debug("Failed to convert", exc_info=e)
            if option.required:
                raise errors.ConverterFailure(
                    f"Conversion failed for option {option.name!r}", opt=option, raw=raw
                ) from e

            out[option.name] = option.default
            _LOGGER.debug("Option has a default value, shifting to the next parameter")
            self.undo()
        else:
            _LOGGER.debug("Successfully converted %s to %s", raw, arg)
            out[option.name] = arg

    async def _greedy_convert(self, raw: str, option: commands.base.OptionLike, out: t.Dict[str, t.Any]) -> None:
        out[option.name] = args = []
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
        callback_or_type: t.Union[
            t.Callable[[str], t.Union[T, t.Coroutine[t.Any, t.Any, T]]], t.Type[BaseConverter[T]]
        ],
    ) -> T:
        callback_or_type = CONVERTER_TYPE_MAPPING.get(callback_or_type, callback_or_type)
        _LOGGER.debug("Attempting to convert %s to %s", value, callback_or_type)
        conversion_func = callback_or_type
        if inspect.isclass(callback_or_type) and issubclass(callback_or_type, BaseConverter):
            conversion_func = callback_or_type(self.ctx).convert

        converted = conversion_func(value)  # type: ignore
        if inspect.iscoroutine(converted):
            assert isinstance(converted, t.Awaitable)
            converted = await converted

        converted = t.cast(T, converted)
        return converted

    def _validate(self, option: commands.base.OptionLike, arg: t.Any) -> None:
        if option.max_length and len(arg) > option.max_length:
            raise errors.InvalidArgument("Value too long", opt=option, value=arg)
        if option.min_length and len(arg) < option.min_length:
            raise errors.InvalidArgument("Value too short", opt=option, value=arg)

        if option.min_value is not None and arg < option.min_value:
            raise errors.InvalidArgument("Value too small", opt=option, value=arg)
        if option.max_value is not None and arg > option.max_value:
            raise errors.InvalidArgument("Value too big", opt=option, value=arg)
        if option.choices and arg not in option.choices:
            raise errors.InvalidArgument("Value not in available choices", opt=option, value=arg)

        if option.channel_types and isinstance(arg, hikari.PartialChannel) and arg.type not in option.channel_types:
            raise errors.InvalidArgument("Invalid channel type", opt=option, value=arg)
