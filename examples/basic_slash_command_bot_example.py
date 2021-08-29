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
    @property
    def description(self):
        return "Checks that the bot is alive"

    @property
    def options(self):
        return []

    async def callback(self, context):
        # To send an ephemeral message instead pass the kwarg:
        # flags=hikari.MessageFlag.EPHEMERAL
        # e.g. await context.respond("Pong!", flags=hikari.MessageFlag.EPHEMERAL)
        await context.respond("Pong!")

    @property
    def enabled_guilds(self):
        # Returning None here means that the slash command is global.
        # To enable for specific guilds, a sequence of guild IDs should be returned instead
        return None


bot.add_slash_command(Ping)
bot.run()
