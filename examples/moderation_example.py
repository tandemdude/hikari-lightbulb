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

bot = hikari.GatewayBot(token="...")
client = lightbulb.client_from_app(bot)

bot.subscribe(hikari.StartingEvent, client.start)


@client.register()
class Ban(
    lightbulb.SlashCommand,
    name="ban",
    description="Bans a user from the server",
):
    # Order of options go from top to bottom
    user = lightbulb.user("user", "The user to ban")
    # Give non-required options a default value (e.g. default=None)
    # Non-required options MUST appear after required options
    # Required options do not have a default value
    reason = lightbulb.string("reason", "Reason for the ban", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        """Ban a user from the server with an optional reason"""
        if not ctx.guild_id:
            await ctx.respond("This command can only be used in a guild.")
            return

        # Create a deferred response as the ban may take longer than 3 seconds
        await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
        # Perform the ban
        await ctx.app.rest.ban_user(ctx.guild_id, self.user.id, reason=self.reason or hikari.UNDEFINED)
        # Provide feedback to the moderator
        await ctx.respond(f"Banned {self.user.mention}.\n**Reason:** {self.reason or 'No reason provided.'}")


@client.register()
class Purge(
    lightbulb.SlashCommand,
    name="purge",
    description="Purge a certain amount of messages from a channel",
):
    count = lightbulb.integer("count", "The amount of messages to purge", max_value=100, min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        """Purge a certain amount of messages from a channel"""
        if not ctx.guild_id:
            await ctx.respond("This command can only be used in a server.")
            return

        # Fetch messages that are not older than 14 days in the channel the command is invoked in
        # Messages older than 14 days cannot be deleted by bots, so this is a necessary precaution
        messages = (
            await ctx.app.rest.fetch_messages(ctx.channel_id)
            .take_until(
                lambda m: datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14) > m.created_at
            )
            .limit(self.count)
        )
        if messages:
            await ctx.app.rest.delete_messages(ctx.channel_id, messages)
            await ctx.respond(f"Purged {len(messages)} messages.")
        else:
            await ctx.respond("Could not find any messages younger than 14 days!")


bot.run()
