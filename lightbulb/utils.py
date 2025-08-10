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

__all__ = ["EMPTY", "FloatEnum", "StrEnum", "get_command_data", "maybe_await", "to_choices"]

import enum
import inspect
import sys
import typing as t
from collections.abc import Sequence

from lightbulb.internal import marker

if t.TYPE_CHECKING:
    from lightbulb.commands import commands
    from lightbulb.commands import groups
    from lightbulb.commands import options
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


def get_command_data(
    command: commands.CommandBase | type[commands.CommandBase] | groups.Group | groups.SubGroup,
) -> commands.CommandData:
    """
    Utility method to get the command data dataclass for a command instance, command class, group, or subgroup.

    Args:
        command: The command instance, command class, group, or subgroup to get the command data for.

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
    return t.cast("T", item)


ChoiceT = t.TypeVar("ChoiceT", str, int, float)


# fmt: off
if sys.version_info >= (3, 11):
    StrEnum = enum.StrEnum
    """
    Alias to ``enum.StrEnum`` in Python versions 3.11 or later, otherwise a
    custom enum base class for compatibility.

    See Also:
        :func:`~to_choices`
    """
else:
    class StrEnum(str, enum.Enum):
        """
        Alias to ``enum.StrEnum`` in Python versions 3.11 or later, otherwise a
        custom enum base class for compatibility.

        See Also:
            :func:`~to_choices`
        """
class FloatEnum(float, enum.Enum):  # noqa: E302
    """
    Custom enum base class for enums with float values.

    See Also:
        :func:`~to_choices`
    """
# fmt: on


@t.overload
def to_choices(raw: Sequence[ChoiceT], localize: bool = False) -> Sequence[options.Choice[ChoiceT]]: ...
@t.overload
def to_choices(raw: Sequence[tuple[str, ChoiceT]], localize: bool = False) -> Sequence[options.Choice[ChoiceT]]: ...
@t.overload
def to_choices(raw: type[StrEnum], localize: bool = False) -> Sequence[options.Choice[str]]: ...
@t.overload
def to_choices(raw: type[enum.IntEnum], localize: bool = False) -> Sequence[options.Choice[int]]: ...
@t.overload
def to_choices(raw: type[FloatEnum], localize: bool = False) -> Sequence[options.Choice[float]]: ...
def to_choices(
    raw: Sequence[t.Any] | Sequence[tuple[str, t.Any]] | type[StrEnum] | type[enum.IntEnum] | type[FloatEnum],
    localize: bool = False,
) -> Sequence[options.Choice[t.Any]]:
    """
    Convert various values to :obj:`~lightbulb.commands.options.Choice` objects for use within command options.

    When using enums to define choices, you should use the enum types exported by this module where available
    (:obj:`~StrEnum`, :obj:`~FloatEnum`). This ensures that your type checker doesn't complain. If you are using
    Python 3.11 or newer, you may use :obj:`enum.StrEnum` as the one provided by this module is just an alias. For
    integer enums you should always use the :obj:`enum.IntEnum` class.

    Args:
        raw: The values to convert to :obj:`~lightbulb.commands.options.Choice` objects.
        localize: Whether the name of the choice should be interpreted as a localization key.

    Returns:
        A sequence of :obj:`~lightbulb.commands.options.Choice` objects.

    Example:

        Using sequences as the input:

        .. code-block:: python

            >>> lightbulb.utils.to_choices(["foo", "bar", "baz"])
            [Choice("foo", "foo"), Choice("bar", "bar"), Choice("baz", "baz)]
            >>> lightbulb.utils.to_choices([1, 2, 3])
            [Choice("1", 1), Choice("2", 2), Choice("3", 3)]
            >>> lightbulb.utils.to_choices([1.5, 2.5, 3.5])
            [Choice("1", 1.5), Choice("2", 2.5), Choice("3", 3.5)]
            >>> lightbulb.utils.to_choices([("foo", "val1"), ("bar", "val2"), ("baz", "val3")])
            [Choice("foo", "val1"), Choice("bar", "val2"), Choice("baz", "val3")]
            >>> lightbulb.utils.to_choices([("foo", 1), ("bar", 2), ("baz", 3)])
            [Choice("foo", 1), Choice("bar", 2), Choice("baz", 3)]
            >>> lightbulb.utils.to_choices([("foo", 1.5), ("bar", 2.5), ("baz", 3.5)])
            [Choice("foo", 1.5), Choice("bar", 2.5), Choice("baz", 3.5)]

        Using enums as the input:

        .. code-block:: python

            >>> class StrChoices(lightbulb.utils.StrEnum):
            ...     FOO = "foo"
            ...     BAR = "bar"
            ...     BAZ = "baz"
            >>> lightbulb.utils.to_choices(StrChoices)
            [Choice("FOO", "foo"), Choice("BAR", "bar"), Choice("BAZ", "baz")]
            >>> class IntChoices(enum.IntEnum):
            ...     FOO = 1
            ...     BAR = 2
            ...     BAZ = 3
            >>> lightbulb.utils.to_choices(IntChoices)
            [Choice("FOO", 1), Choice("BAR", 2), Choice("BAZ", 3)]
            >>> class FloatChoices(lightbulb.utils.FloatEnum):
            ...     FOO = 1.5
            ...     BAR = 2.5
            ...     BAZ = 3.5
            [Choice("FOO", 1.5), Choice("BAR", 2.5), Choice("BAZ", 3.5)]

    .. versionadded:: 3.1.2
    """
    from lightbulb.commands.options import Choice

    if isinstance(raw, Sequence):
        if not raw:
            return []

        if isinstance(raw[0], tuple):
            return [Choice(tup[0], tup[1], localize) for tup in t.cast("Sequence[tuple[str, t.Any]]", raw)]
        return [Choice(str(elem), elem, localize) for elem in t.cast("Sequence[t.Any]", raw)]

    # noinspection PyUnreachableCode
    return [Choice(value.name, value.value, localize) for value in raw]
