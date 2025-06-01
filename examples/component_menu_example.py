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
import asyncio

import hikari

import lightbulb

bot = hikari.GatewayBot(token="...")
client = lightbulb.client_from_app(bot)

bot.subscribe(hikari.StartingEvent, client.start)

ASSIGNABLE_ROLES: dict[str, int] = {
    "Gaming": 000,
    "Movies": 123,
    "Coding": 456,
    "Drawing": 789,
}


class ConfirmationMenu(lightbulb.components.Menu):
    def __init__(self, member: hikari.Member) -> None:
        self.member = member

        self.cancel = self.add_interactive_button(hikari.ButtonStyle.DANGER, self.on_cancel, label="Cancel")
        self.confirm = self.add_interactive_button(hikari.ButtonStyle.SUCCESS, self.on_confirm, label="Confirm")

        self.confirmed: bool = False

    async def predicate(self, ctx: lightbulb.components.MenuContext) -> bool:
        if ctx.user.id != self.member.id:
            await ctx.respond("You are not permitted to use this menu", ephemeral=True)
            return False

        return True

    async def on_cancel(self, ctx: lightbulb.components.MenuContext) -> None:
        await ctx.respond("Cancelled", edit=True, components=[])
        ctx.stop_interacting()

    async def on_confirm(self, ctx: lightbulb.components.MenuContext) -> None:
        await ctx.respond("Confirmed", edit=True, components=[])
        self.confirmed = True
        ctx.stop_interacting()


class RoleSelectorMenu(lightbulb.components.Menu):
    def __init__(self, member: hikari.Member) -> None:
        self.member = member
        self.select = self.add_text_select(list(ASSIGNABLE_ROLES.keys()), self.on_select, placeholder="Select a Role")

    async def predicate(self, ctx: lightbulb.components.MenuContext) -> bool:
        if ctx.user.id != self.member.id:
            await ctx.respond("You are not permitted to use this menu", ephemeral=True)
            return False

        return True

    async def on_select(self, ctx: lightbulb.components.MenuContext) -> None:
        selected_values = ctx.selected_values_for(self.select)
        # We know there will only be one selected value because 'min_values' and 'max_values'
        # are both set to 1 for the select component
        role_to_add = ASSIGNABLE_ROLES[selected_values[0]]

        # Confirm with the user whether they want to claim the role
        confirm_menu = ConfirmationMenu(self.member)
        await ctx.respond(
            f"Are you sure you want to claim the {selected_values[0]!r} role?", edit=True, components=confirm_menu
        )
        try:
            # Extend the timeout of this menu to account for the sub-menu
            ctx.extend_timeout(30)
            await confirm_menu.attach(client, timeout=30)
        except asyncio.TimeoutError:
            await ctx.respond("Timed out", edit=True, components=[])

        if not confirm_menu.confirmed:
            return

        await bot.rest.add_role_to_member(self.member.guild_id, self.member.id, role_to_add)
        await ctx.respond(f"Role {selected_values[0]!r} assigned successfully.", edit=True, components=[])


@client.register
class GetRole(
    lightbulb.SlashCommand,
    name="get-role",
    description="Assign yourself a role",
    dm_enabled=False,
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        assert ctx.member is not None

        menu = RoleSelectorMenu(ctx.member)
        resp = await ctx.respond("Pick the role you want", components=menu)
        try:
            await menu.attach(client, timeout=30)
        except asyncio.TimeoutError:
            await ctx.edit_response(resp, "Timed out", components=[])


if __name__ == "__main__":
    bot.run()
