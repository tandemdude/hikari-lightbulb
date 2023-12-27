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

import enum
import typing as t

__all__ = ["HookType", "pre_invoke", "on_invoke", "post_invoke"]

HookFunctionT = t.TypeVar("HookFunctionT", bound=t.Callable[..., t.Any])


class HookType(enum.Enum):
    PRE_INVOKE = enum.auto()
    ON_INVOKE = enum.auto()
    POST_INVOKE = enum.auto()


_HOOK_TYPE_ATTR = "__command_hook_type__"


def pre_invoke(func: HookFunctionT) -> HookFunctionT:
    setattr(func, _HOOK_TYPE_ATTR, HookType.PRE_INVOKE)
    return func


def on_invoke(func: HookFunctionT) -> HookFunctionT:
    setattr(func, _HOOK_TYPE_ATTR, HookType.ON_INVOKE)
    return func


def post_invoke(func: HookFunctionT) -> HookFunctionT:
    setattr(func, _HOOK_TYPE_ATTR, HookType.POST_INVOKE)
    return func
