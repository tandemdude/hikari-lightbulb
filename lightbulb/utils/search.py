# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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

__all__: typing.Final[typing.List[str]] = ["get", "find"]

import typing
from operator import attrgetter

T = typing.TypeVar("T")


def get(sequence: typing.Iterable[T], **attrs) -> typing.Optional[T]:
    """
    Get the first item from an iterable that matches all the parameters
    specified, or return ``None`` if no matching item was found.

    Args:
        sequence (Iterable[ T ]): Iterable to search through.

    Keyword Args:
        **attrs: Attributes to match.

    Example:
        Searching for a member with a specific username in the bot's cached members.

        .. code-block:: python

            members = bot.get_members_view_for_guild(ctx.guild_id)
            member = lightbulb.utils.get(members.values(), username="foo")

    See Also:
        :obj:`~find`
    """
    flattened = [(attrgetter(attr), value) for attr, value in attrs.items()]

    for item in sequence:
        if all([getter(item) == value for getter, value in flattened]):
            return item
    return None


def find(sequence: typing.Iterable[T], predicate: typing.Callable[[T], bool]) -> typing.Optional[T]:
    """
    Find the first item from an iterable that passes for the predicate specified,
    or return ``None`` if no matching item was found.

    Args:
        sequence (Iterable[ T ]): Iterable to search through.
        predicate (Callable[ [ T ], :obj:`bool` ]): Function to evaluate if the item
            is the correct one or not. It should return a boolean or boolean-like result.

    Example:
        Searching for a member with a specific username in the bot's cached members.

        .. code-block:: python

            members = bot.get_members_view_for_guild(ctx.guild_id)
            member = lightbulb.utils.find(members.values(), lambda m: m.username == "foo")

    See Also:
        :obj:`~get`
    """
    for item in sequence:
        if predicate(item):
            return item
    return None
