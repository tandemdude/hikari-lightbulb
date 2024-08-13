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
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.BAN_MEMBERS,
):
    # Order of options go from top to bottom
    user = lightbulb.user("user", "The user to ban")
    # Give non-required options a default value (e.g. default=None)
    # Non-required options MUST appear after required options
    # Required options do not have a default value
    reason = lightbulb.string("reason", "Reason for the ban", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, rest: hikari.api.RESTClient) -> None:
        """Ban a user from the server with an optional reason."""
        if not ctx.guild_id:
            await ctx.respond("This command can only be used in a guild.")
            return

        # Create a deferred response as the ban may take longer than 3 seconds
        await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
        # Perform the ban
        await rest.ban_user(ctx.guild_id, self.user.id, reason=self.reason or hikari.UNDEFINED)
        # Provide feedback to the moderator
        await ctx.respond(f"Banned {self.user.mention}.\n**Reason:** {self.reason or 'No reason provided.'}")


@client.register()
class Purge(
    lightbulb.SlashCommand,
    name="purge",
    description="Purge a certain amount of messages from a channel",
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.MANAGE_MESSAGES,
):
    count = lightbulb.integer("count", "The amount of messages to purge", max_value=100, min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, rest: hikari.api.RESTClient) -> None:
        """Purge a certain amount of messages from a channel."""
        if not ctx.guild_id:
            await ctx.respond("This command can only be used in a server.")
            return

        # Fetch messages that are not older than 14 days in the channel the command is invoked in
        # Messages older than 14 days cannot be deleted by bots, so this is a necessary precaution
        messages = (
            await rest.fetch_messages(ctx.channel_id)
            .take_until(
                lambda m: datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14) > m.created_at
            )
            .limit(self.count)
        )
        if messages:
            await rest.delete_messages(ctx.channel_id, messages)
            await ctx.respond(f"Purged {len(messages)} messages.")
        else:
            await ctx.respond("Could not find any messages younger than 14 days!")


if __name__ == "__main__":
    bot.run()
