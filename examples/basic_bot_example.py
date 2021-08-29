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
import lightbulb
import hikari

bot = lightbulb.Bot(prefix="!", token="YOUR_TOKEN", intents=hikari.Intents.ALL)


@bot.listen(hikari.ShardReadyEvent)
async def ready_listener(event):
    print("The bot is ready!")


@bot.command()
async def ping(ctx):
    """Checks that the bot is alive"""
    await ctx.respond("Pong!")


@bot.command()
async def add(ctx, num1: int, num2: int):
    """Adds the two given numbers together"""
    await ctx.respond(f"{num1} + {num2} = {num1 + num2}")


@bot.command()
async def greet(ctx, user: hikari.User):
    """Greets the specified user"""
    await ctx.respond(f"Hello {user.mention}!")


bot.run()
