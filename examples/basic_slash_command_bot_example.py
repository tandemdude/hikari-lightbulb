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
import hikari

import lightbulb

bot = lightbulb.Bot(prefix="!", token="YOUR_TOKEN", intents=hikari.Intents.ALL)


class Ping(lightbulb.slash_commands.SlashCommand):
    description = "Checks that the bot is alive"
    # None here means that the slash command is global. To enable for specific guilds,
    # it should instead be a sequence of guild IDs.
    enabled_guilds = None
    options = []

    # This function is called when the slash command is invoked by a user. It **must** be called "callback"
    # otherwise the interaction **will** fail.
    async def callback(self, context):
        # To send an ephemeral message instead pass the kwarg:
        # flags=hikari.MessageFlag.EPHEMERAL
        # e.g. await context.respond("Pong!", flags=hikari.MessageFlag.EPHEMERAL)
        await context.respond("Pong!")


bot.add_slash_command(Ping)
bot.run()
