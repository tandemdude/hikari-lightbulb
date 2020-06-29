# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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
from lightbulb import context
from lightbulb import commands
from lightbulb import errors


async def _guild_only(ctx: context.Context) -> bool:
    if ctx.message.guild_id is None:
        raise errors.OnlyInGuild(ctx)
    return True


async def _dm_only(ctx: context.Context) -> bool:
    if ctx.message.guild_id is not None:
        raise errors.OnlyInDM(ctx)
    return True


async def _owner_only(ctx: context.Context) -> bool:
    if not ctx.bot.owner_ids:
        await ctx.bot.fetch_owner_ids()

    if ctx.message.author.id not in ctx.bot.owner_ids:
        raise errors.NotOwner(ctx)
    return True


def guild_only():
    """
    A decorator that prevents a command from being used in direct messages.
    """

    def decorate(command: commands.Command) -> commands.Command:
        command.add_check(_guild_only)
        return command

    return decorate


def dm_only():
    """
    A decorator that prevents a command from being used in a guild.

    Example:

        .. code-block:: python

            bot = lightbulb.Bot(token="token_here", prefix="!")

            @lightbulb.dm_only()
            @bot.command()
            async def foo(ctx):
                await ctx.reply("bar")
    """

    def decorate(command: commands.Command) -> commands.Command:
        command.add_check(_dm_only)
        return command

    return decorate


def owner_only():
    """
    A decorator that prevents a command from being used by anyone other than the owner of the application.
    """

    def decorate(command: commands.Command) -> commands.Command:
        command.add_check(_owner_only)
        return command

    return decorate
