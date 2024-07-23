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

__all__ = ["EMPTY", "get_command_data"]

import inspect
import typing as t

from lightbulb.internal import marker

if t.TYPE_CHECKING:
    from lightbulb.commands import commands
    from lightbulb.internal import types

T = t.TypeVar("T")

EMPTY: t.Final[t.Any] = marker.Marker("EMPTY")
"""Placeholder object returned when attempting to get the value for an option on a class instead of an instance.

Example:

    .. code-block:: python

        class YourCommand(lightbulb.SlashCommand, ...):
            option = lightbulb.string(...)
            ...

        # The following will be True
        YourCommand.option is lightbulb.utils.EMPTY
"""


def get_command_data(command: commands.CommandBase | type[commands.CommandBase]) -> commands.CommandData:
    """
    Utility method to get the command data dataclass for a command instance or command class.

    Args:
        command: The command instance or command class to get the command data for.

    Returns:
        :obj:`~lightbulb.commands.commands.CommandData`: Command data dataclass for the given command.
    """
    return command._command_data


async def maybe_await(item: types.MaybeAwaitable[T]) -> T:
    """
    Await the given item if it is a coroutine, otherwise just return the given item.

    Args:
        item: The item to maybe await.

    Returns:
        The item, or the return once the item was awaited.
    """
    if inspect.iscoroutine(item):
        return await item
    return t.cast(T, item)
