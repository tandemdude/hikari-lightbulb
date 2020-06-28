# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
#
# This file is part of Hikari Command Handler.
#
# Hikari Command Handler is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari Command Handler is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari Command Handler. If not, see <https://www.gnu.org/licenses/>.
import typing
import logging
import inspect


class Command:
    """
    A command that can be invoked by a user. When invoked, the :attr:`.commands.Command.callback` will be called
    with a set argument ``ctx``, and instance of the :class:`.context.Context` class, and any other arguments supplied
    by the user.

    Args:
        callable (:obj:`typing.Callable`): The callable object linked to the command.
    """
    def __init__(self, callable: typing.Callable) -> None:
        self.callback = callable
        self.name = callable.__name__
        self.help: typing.Optional[str] = inspect.getdoc(callable)

    async def __call__(self, *args, **kwargs) -> None:
        await self.callback(*args)
