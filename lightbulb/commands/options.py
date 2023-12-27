# -*- coding: utf-8 -*-
# Copyright © tandemdude 2023-present
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

import typing as t

import attr
import hikari

if t.TYPE_CHECKING:
    from lightbulb import commands

__all__ = ["OptionData", "Option", "string"]

T = t.TypeVar("T")
D = t.TypeVar("D")


def _non_undefined_or(item: hikari.UndefinedOr[T], default: D) -> t.Union[T, D]:
    return item if item is not hikari.UNDEFINED else default


@attr.define(frozen=True, kw_only=True, slots=True)
class OptionData(t.Generic[D]):
    type: hikari.OptionType
    name: str
    description: str
    default: hikari.UndefinedOr[D]
    choices: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED  # TODO
    channel_types: hikari.UndefinedOr[t.Sequence[hikari.ChannelType]] = hikari.UNDEFINED
    min_value: hikari.UndefinedOr[t.Union[int, float]] = hikari.UNDEFINED
    max_value: hikari.UndefinedOr[t.Union[int, float]] = hikari.UNDEFINED
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED
    autocomplete: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED  # TODO
    localizations: t.Any = hikari.UNDEFINED  # TODO

    def to_command_option(self) -> hikari.CommandOption:
        return hikari.CommandOption(
            type=self.type,
            name=self.name,
            description=self.description,
            is_required=self.default is not hikari.UNDEFINED,
            choices=_non_undefined_or(self.choices, None),
            channel_types=_non_undefined_or(self.channel_types, None),
            min_value=_non_undefined_or(self.min_value, None),
            max_value=_non_undefined_or(self.max_value, None),
            min_length=_non_undefined_or(self.min_length, None),
            max_length=_non_undefined_or(self.max_length, None),
            autocomplete=self.autocomplete is not hikari.UNDEFINED,
        )


class Option(t.Generic[T, D]):
    __slots__ = ("_data", "_unbound_default")

    def __init__(self, data: OptionData[D], default_when_not_bound: T) -> None:
        self._data = data
        self._unbound_default = default_when_not_bound

    def __get__(self, instance: t.Optional[commands.CommandBase], owner: t.Type[commands.CommandBase]) -> t.Union[T, D]:
        if instance is None:
            return self._unbound_default

        if instance._current_context is None:
            # TODO - logging?
            return self._unbound_default

        # I have absolutely no idea how to fix this type error
        return instance._.resolve_option(instance._current_context, self)  # type: ignore[arg-type]


def string(
    name: str,
    description: str,
    default: hikari.UndefinedNoneOr[D] = hikari.UNDEFINED,
    choices: t.Any = hikari.UNDEFINED,  # TODO
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: t.Any = hikari.UNDEFINED,  # TODO
) -> str:
    return t.cast(
        str,
        Option(
            OptionData(
                type=hikari.OptionType.STRING,
                name=name,
                description=description,
                default=default,
                choices=choices,
                min_length=min_length,
                max_length=max_length,
                autocomplete=autocomplete,
            ),
            "",
        ),
    )
