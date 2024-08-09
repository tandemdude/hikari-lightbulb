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
import hikari

import lightbulb

bot = hikari.GatewayBot(token="...")
client = lightbulb.client_from_app(bot)

bot.subscribe(hikari.StartingEvent, client.start)


@client.register()
class Ping(
    lightbulb.SlashCommand,
    name="ping",
    description="Checks that the bot is alive",
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        """Checks that the bot is alive"""
        await ctx.respond("Pong!")


@client.register()
class Echo(
    lightbulb.SlashCommand,
    name="echo",
    description="Repeats the user's input",
):
    text = lightbulb.string("text", "Text to repeat")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        """Repeats the user's input"""
        await ctx.respond(self.text)


@client.register()
class Add(
    lightbulb.SlashCommand,
    name="add",
    description="Adds the two given numbers together",
):
    # Order of options go from top to bottom
    num1 = lightbulb.integer("num1", "First number")
    num2 = lightbulb.integer("num2", "Second number")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        """Adds the two given numbers together"""
        await ctx.respond(f"{self.num1} + {self.num2} = {self.num1 + self.num2}")


bot.run()
