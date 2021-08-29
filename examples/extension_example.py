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


class ExamplePlugin(lightbulb.Plugin):
    @lightbulb.command()
    async def ping(self, ctx):
        """Checks that the bot is alive"""
        await ctx.respond("Pong!")


class ExampleSlashCommand(lightbulb.slash_commands.SlashCommand):
    @property
    def name(self):
        return "ping"

    @property
    def description(self):
        return "Checks that the bot is alive"

    @property
    def options(self):
        return []

    @property
    def enabled_guilds(self):
        return None

    async def callback(self, context) -> None:
        await context.respond("Pong!")


def load(bot):
    bot.add_plugin(ExamplePlugin())
    bot.add_slash_command(ExampleSlashCommand)


def unload(bot):
    bot.remove_plugin("ExamplePlugin")
    # Name passed in here must be the name of the slash command
    # as discord sees it. So "ping" in the above example, not "exampleslashcommand"
    bot.remove_slash_command("ping")
