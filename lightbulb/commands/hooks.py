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
