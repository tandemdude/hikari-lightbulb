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
__all__ = [
    "CommandOrGroup",
    "DeferredRegistrationCallback",
    "ErrorHandler",
    "MaybeAwaitable",
]

import typing as t
from collections.abc import Callable
from collections.abc import Iterable

import hikari
from linkd.utils import MaybeAwaitable

if t.TYPE_CHECKING:
    from lightbulb import exceptions
    from lightbulb.commands import commands
    from lightbulb.commands import groups

T = t.TypeVar("T")

CommandOrGroup: t.TypeAlias = t.Union["groups.Group", type["commands.CommandBase"]]
# Annoyingly can't replace this with 'Callable' because the concatenate I use isn't supported
ErrorHandler: t.TypeAlias = t.Callable[
    "t.Concatenate[exceptions.ExecutionPipelineFailedException, ...]", MaybeAwaitable[bool]
]
DeferredRegistrationCallback: t.TypeAlias = Callable[
    [CommandOrGroup], MaybeAwaitable[tuple[Iterable[hikari.Snowflakeish], bool] | None]
]
