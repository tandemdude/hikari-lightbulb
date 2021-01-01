# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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

import inspect
import typing

from lightbulb.utils import nav
from lightbulb.utils import pag
from lightbulb.utils import search
from lightbulb.utils.nav import *
from lightbulb.utils.pag import *
from lightbulb.utils.search import *

__all__: typing.Final[typing.List[str]] = [*nav.__all__, *pag.__all__, *search.__all__, "maybe_await"]


async def maybe_await(callable_, *args, **kwargs):
    result = callable_(*args, **kwargs)
    if inspect.iscoroutine(result):
        result = await result
    return result
