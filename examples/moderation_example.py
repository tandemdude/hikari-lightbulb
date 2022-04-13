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
import datetime

import hikari

import lightbulb

bot = lightbulb.BotApp(token="YOUR_TOKEN", intents=hikari.Intents.ALL_UNPRIVILEGED)


@bot.command()
@lightbulb.option("reason", "Reason for the ban", required=False)
@lightbulb.option("user", "The user to ban.", type=hikari.User)
@lightbulb.command("ban", "Ban a user from the server.")
@lightbulb.implements(lightbulb.SlashCommand)
async def ban(ctx: lightbulb.SlashContext) -> None:
    """Ban a user from the server with an optional reason."""
    if not ctx.guild_id:
        await ctx.respond("This command can only be used in a guild.")
        return

    # Create a deferred response as the ban may take longer than 3 seconds
    await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    # Perform the ban
    await ctx.app.rest.ban_user(ctx.guild_id, ctx.options.user.id, reason=ctx.options.reason or hikari.UNDEFINED)
    # Provide feedback to the moderator
    await ctx.respond(f"Banned {ctx.options.user.mention}.\n**Reason:** {ctx.options.reason or 'No reason provided.'}")


@bot.command()
@lightbulb.option("count", "The amount of messages to purge.", type=int, max_value=100, min_value=1)
# You may also use pass_options to pass the options directly to the function
@lightbulb.command("purge", "Purge a certain amount of messages from a channel.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def purge(ctx: lightbulb.SlashContext, count: int) -> None:
    """Purge a certain amount of messages from a channel."""
    if not ctx.guild_id:
        await ctx.respond("This command can only be used in a server.")
        return

    # Fetch messages that are not older than 14 days in the channel the command is invoked in
    # Messages older than 14 days cannot be deleted by bots, so this is a necessary precaution
    messages = (
        await ctx.app.rest.fetch_messages(ctx.channel_id)
        .take_until(lambda m: datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14) > m.created_at)
        .limit(count)
    )
    if messages:
        await ctx.app.rest.delete_messages(ctx.channel_id, messages)
        await ctx.respond(f"Purged {len(messages)} messages.")
    else:
        await ctx.respond("Could not find any messages younger than 14 days!")


bot.run()
