# -*- coding: utf-8 -*-
# Copyright (c) 2023-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

import enum
import typing as t

from lightbulb.internal import di

if t.TYPE_CHECKING:
    from lightbulb import context

__all__ = ["HookType", "pre_invoke", "on_invoke", "post_invoke"]


class HookType(enum.Enum):
    PRE_INVOKE = enum.auto()
    ON_INVOKE = enum.auto()
    POST_INVOKE = enum.auto()


def pre_invoke(func: t.Callable[..., t.Awaitable[t.Any]]) -> t.Callable[[context.Context], t.Awaitable[t.Any]]:
    replacement = di.LazyInjecting(func)
    setattr(replacement, "__command_hook_type__", HookType.PRE_INVOKE)
    return replacement


def on_invoke(func: t.Callable[..., t.Awaitable[t.Any]]) -> t.Callable[[context.Context], t.Awaitable[t.Any]]:
    replacement = di.LazyInjecting(func)
    setattr(replacement, "__command_hook_type__", HookType.ON_INVOKE)
    return replacement


def post_invoke(func: t.Callable[..., t.Awaitable[t.Any]]) -> t.Callable[[context.Context], t.Awaitable[t.Any]]:
    replacement = di.LazyInjecting(func)
    setattr(replacement, "__command_hook_type__", HookType.POST_INVOKE)
    return replacement
