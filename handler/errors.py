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
from hikari.events import base


class CommandErrorEvent(base.Event):
    """Event type to subscribe to for the processing of all command errors raised by the handler"""

    def __init__(self, error):
        self.error = error


class CommandError(Exception):
    """Base exception for the command handler"""

    pass


class CommandNotFound(CommandError):
    """Exception raised when a command when attempted to be invoked but one with that name could not be found"""

    def __init__(self, invoked_with: str):
        self.invoked_with = invoked_with
