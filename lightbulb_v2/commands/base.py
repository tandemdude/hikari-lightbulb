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
__all__ = ["OptionLike", "CommandLike", "Command"]

import abc
import dataclasses
import typing as t

import hikari

if t.TYPE_CHECKING:
    from lightbulb_v2 import checks
    from lightbulb_v2 import context


@dataclasses.dataclass
class OptionLike:
    name: str
    description: str
    arg_type: t.Type[t.Any] = str
    required: t.Optional[bool] = None
    choices: t.Optional[t.Sequence[t.Union[str, int, float, hikari.CommandChoice]]] = None
    channel_types: t.Optional[t.Sequence[hikari.ChannelType]] = None
    default: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED


@dataclasses.dataclass
class CommandLike:
    name: str
    description: str
    options: t.MutableMapping[str, OptionLike] = dataclasses.field(default_factory=dict)
    checks: t.Sequence[checks.Check] = dataclasses.field(default_factory=list)
    cooldown_manager: t.Optional[...] = None  # TODO
    error_handler: t.Optional[t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]] = None


class Command(abc.ABC):
    pass
