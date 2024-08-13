# -*- coding: utf-8 -*-
# Copyright (c) 2023-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
        """Checks that the bot is alive."""
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
        """Repeats the user's input."""
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
        """Adds the two given numbers together."""
        await ctx.respond(f"{self.num1} + {self.num2} = {self.num1 + self.num2}")


if __name__ == "__main__":
    bot.run()
