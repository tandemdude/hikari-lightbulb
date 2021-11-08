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

bot = lightbulb.Bot(prefix="!", token="YOUR_TOKEN")


class Ping(lightbulb.slash_commands.SlashCommand):
    description = "Checks that the bot is alive"
    # enabled_guilds is set to an empty list by default - this means that the command
    # will be global. To restrict the command to certain guilds only you would set enabled_guilds
    # to a sequence of guild IDs as seen below:
    # enabled_guilds = [123456, 92649673]

    # This function is called when the slash command is invoked by a user. It **must** be called "callback"
    # otherwise the interaction **will** fail.
    async def callback(self, context):
        # To send an ephemeral message instead pass the kwarg:
        # flags=hikari.MessageFlag.EPHEMERAL
        # e.g. await context.respond("Pong!", flags=hikari.MessageFlag.EPHEMERAL)
        await context.respond("Pong!")


class Echo(lightbulb.slash_commands.SlashCommand):
    description = "Repeats the user's input"
    # Defining command options
    text: str = lightbulb.slash_commands.Option("Text to repeat")
    # To create an optional command option you would need to typehint the attribute
    # as Optional. See below:
    # text: typing.Optional[str] = Option(...)
    # available option types can be seen in the documentation:
    # https://hikari-lightbulb.readthedocs.io/en/latest/slash-commands.html

    async def callback(self, context):
        # Respond with the value of the 'text' option - the text that the user input.
        await context.respond(context.options.text)


bot.add_slash_command(Ping)
bot.add_slash_command(Echo)
bot.run()
