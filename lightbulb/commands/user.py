# -*- coding: utf-8 -*-
# Copyright © tandemdude 2020-present
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

__all__ = ["UserCommand"]

import typing as t

from lightbulb.commands import base


class UserCommand(base.ApplicationCommand):
    """
    An implementation of :obj:`~.commands.base.Command` representing a user context menu command.

    See the `API Documentation <https://discord.com/developers/docs/interactions/application-commands#user-commands>`_.
    """

    __slots__ = ()

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.options: t.Dict[str, t.Any] = {}

    def as_create_kwargs(self) -> t.Dict[str, t.Any]:
        raise NotImplementedError
