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
from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from hikari.models import messages

    from handler import commands


class Context:
    def __init__(
        self,
        message: messages.Message,
        prefix: str,
        invoked_with: str,
        command: commands.Command,
    ) -> None:
        self.message: messages.Message = message
        self.prefix: str = prefix
        self.invoked_with: str = invoked_with
        self.command: commands.Command = command
