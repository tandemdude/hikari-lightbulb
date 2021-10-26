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

__all__ = ["PrefixCommand"]

from lightbulb_v2 import context as context_
from lightbulb_v2.commands import base
from lightbulb_v2.utils import parser


class PrefixCommand(base.Command):
    """
    An implementation of :obj:`~.commands.base.Command` representing a prefix command.
    """

    @property
    def signature(self) -> str:
        sig = self.qualname
        if self.options:
            sig += f" {' '.join(f'<{o.name}>' if o.required else f'[{o.name}]' for o in self.options.values())}"
        return sig

    async def invoke(self, context: context_.base.Context) -> None:
        await self.evaluate_checks(context)
        await self.evaluate_cooldowns(context)
        assert isinstance(context, context_.prefix.PrefixContext)
        await parser.Parser(context).inject_args_to_context()
        await self(context)
