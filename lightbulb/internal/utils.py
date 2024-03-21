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

import dataclasses
import inspect
import typing as t

import hikari

from lightbulb.commands import commands
from lightbulb.commands import groups

T = t.TypeVar("T")
D = t.TypeVar("D")


@dataclasses.dataclass(slots=True)
class CommandCollection:
    slash: groups.Group | type[commands.SlashCommand] | None = None
    user: type[commands.UserCommand] | None = None
    message: type[commands.MessageCommand] | None = None

    def put(
        self,
        command: groups.Group | t.Type[commands.CommandBase],
    ) -> None:
        if isinstance(command, groups.Group) or issubclass(command, commands.SlashCommand):
            self.slash = command
        elif issubclass(command, commands.UserCommand):
            self.user = command
        elif issubclass(command, commands.MessageCommand):
            self.message = command
        else:
            raise TypeError("unsupported command passed")


def non_undefined_or(item: hikari.UndefinedOr[T], default: D) -> T | D:
    return item if item is not hikari.UNDEFINED else default


async def maybe_await(item: T | t.Awaitable[T]) -> T:
    if inspect.isawaitable(item):
        return await item
    return t.cast(T, item)
