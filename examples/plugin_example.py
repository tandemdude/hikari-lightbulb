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

bot = lightbulb.BotApp(prefix="!", token="YOUR_TOKEN")


plugin = lightbulb.Plugin("Example Plugin")


@plugin.command()
@lightbulb.option("text", "Text to repeat", modifier=lightbulb.OptionModifier.CONSUME_REST)
@lightbulb.command("echo", "Repeats the user's input")
@lightbulb.implements(lightbulb.PrefixCommand)
async def echo(ctx: lightbulb.Context) -> None:
    await ctx.respond(ctx.options.text)


bot.add_plugin(plugin)
bot.run()
