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

__all__ = ["CommandCollection", "non_undefined_or"]

import dataclasses
import typing as t

import hikari

from lightbulb.commands import commands
from lightbulb.commands import groups

T = t.TypeVar("T")
D = t.TypeVar("D")


@dataclasses.dataclass(slots=True)
class CommandCollection:
    """
    Collection of commands used internally in the Client to allow commands of multiple
    types to share the same name.
    """

    slash: type[commands.SlashCommand] | None = None
    """The collection's slash command."""
    user: type[commands.UserCommand] | None = None
    """The collection's user command."""
    message: type[commands.MessageCommand] | None = None
    """The collection's message command."""

    def put(
        self,
        command: type[commands.CommandBase],
    ) -> None:
        """
        Add a command to the collection. Automatically places it in the correct attribute. If a second
        command of the same type is given then it will replace the first command.

        Args:
            command: The command to add to the collection.

        Returns:
            :obj:`None`
        """
        if issubclass(command, commands.SlashCommand):
            self.slash = command
        elif issubclass(command, commands.UserCommand):
            self.user = command
        elif issubclass(command, commands.MessageCommand):
            self.message = command
        else:
            raise TypeError("unsupported command passed")

    def remove(self, command: groups.Group | type[commands.CommandBase]) -> None:
        """
        Remove a command from the collection. Does nothing if the command is not present in this collection.

        Args:
            command: The command to remove from the collection.

        Returns:
            :obj:`None`
        """
        if self.slash is command:
            self.slash = None
        if self.user is command:
            self.user = None
        if self.message is command:
            self.message = None


def non_undefined_or(item: hikari.UndefinedOr[T], default: D) -> T | D:
    """
    Return the given item if it is not undefined, otherwise return the default.

    Args:
        item: The item that may be undefined.
        default: The default to return when the item is undefined.

    Returns:
        ``item`` or ``default`` depending on whether ``item`` was undefined.
    """
    return item if item is not hikari.UNDEFINED else default
