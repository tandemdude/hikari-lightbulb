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

bot = lightbulb.BotApp(prefix="!", token="YOUR_TOKEN", intents=hikari.Intents.ALL_UNPRIVILEGED)


@bot.listen(hikari.ShardReadyEvent)
async def ready_listener(_):
    print("The bot is ready!")


@bot.command()
@lightbulb.command("ping", "Checks that the bot is alive")
@lightbulb.implements(lightbulb.PrefixCommand)
async def ping(ctx: lightbulb.Context) -> None:
    """Checks that the bot is alive"""
    await ctx.respond("Pong!")


@bot.command()
@lightbulb.option("num2", "Second number", int)
@lightbulb.option("num1", "First number", int)
@lightbulb.command("add", "Adds the two given numbers together")
@lightbulb.implements(lightbulb.PrefixCommand)
async def add(ctx: lightbulb.Context) -> None:
    """Adds the two given numbers together"""
    num1, num2 = ctx.options.num1, ctx.options.num2
    await ctx.respond(f"{num1} + {num2} = {num1 + num2}")


@bot.command()
@lightbulb.option("user", "User to greet", hikari.User)
@lightbulb.command("greet", "Greets the specified user")
@lightbulb.implements(lightbulb.PrefixCommand)
async def greet(ctx: lightbulb.Context) -> None:
    await ctx.respond(f"Hello {ctx.options.user.mention}!")


bot.run()
