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

__all__ = ["implements", "command", "option"]

import typing as t

import hikari

from lightbulb_v2 import commands

if t.TYPE_CHECKING:
    from lightbulb_v2 import context

T = t.TypeVar("T")


def implements(
    *command_types: t.Type[commands.base.Command],
) -> t.Callable[
    [t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]],
    t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]],
]:
    def decorate(
        func: t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]
    ) -> t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]:
        setattr(func, "__cmd_types__", command_types)
        return func

    return decorate


def command(
    name: str, description: str, **kwargs: t.Any
) -> t.Callable[[t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]], commands.base.CommandLike]:
    def decorate(
        func: t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]
    ) -> commands.base.CommandLike:
        return commands.base.CommandLike(func, name, description, **kwargs)

    return decorate


def option(
    name: str, description: str, type: t.Type[t.Any] = str, **kwargs: t.Any
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    kwargs.setdefault("required", kwargs.get("default", hikari.UNDEFINED) is hikari.UNDEFINED)

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        c_like.options[name] = commands.base.OptionLike(name, description, type, **kwargs)
        return c_like

    return decorate
