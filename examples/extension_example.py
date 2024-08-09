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
import lightbulb

loader = lightbulb.Loader()


@loader.command
class Greet(
    lightbulb.SlashCommand,
    name="greet",
    description="Greets the specified user",
):
    user = lightbulb.user("user", "User to greet")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        """Greets the specified user"""
        await ctx.respond(f"Hello, {self.user.mention}!")
