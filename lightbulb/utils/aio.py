# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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

__all__: typing.Final[typing.List[str]] = ["maybe_await"]

import typing

T = typing.TypeVar("T")
T_in = typing.TypeVar("T_in")


async def maybe_await(
    callable_: typing.Callable[[T_in], typing.Union[T, typing.Coroutine[None, None, T]]], *args: T_in, **kwargs: T_in
) -> T:
    result = callable_(*args, **kwargs)

    if isinstance(result, typing.Coroutine):
        return await result

    return result
