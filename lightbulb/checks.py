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
import typing

from lightbulb import context
from lightbulb import commands
from lightbulb import errors

__all__: typing.Final[typing.Tuple[str]] = (
    "guild_only",
    "dm_only",
    "owner_only",
    "check",
)


async def _guild_only(ctx: context.Context) -> bool:
    if ctx.message.guild_id is None:
        raise errors.OnlyInGuild("This command can only be used in a guild")
    return True


async def _dm_only(ctx: context.Context) -> bool:
    if ctx.message.guild_id is not None:
        raise errors.OnlyInDM("This command can only be used in DMs")
    return True


async def _owner_only(ctx: context.Context) -> bool:
    if not ctx.bot.owner_ids:
        await ctx.bot.fetch_owner_ids()

    if ctx.message.author.id not in ctx.bot.owner_ids:
        raise errors.NotOwner("You are not the owner of this bot")
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


def check(check_func: typing.Callable[[context.Context], typing.Coroutine[typing.Any, typing.Any, bool]]):
    """
    A decorator which adds a custom check function to a command. The check function must be a coroutine (async def)
    and take a single argument, which will be the command context.

    This acts as a shortcut to calling :meth:`~.commands.Command.add_check` on a command instance.

    Args:
        check_func (Callable[ [ :obj:`~.context.Context` ], Coroutine[ Any, Any, :obj:`bool` ] ]): The coroutine
            to add to the command as a check.

    Example:

        .. code-block:: python

            async def check_message_contains_hello(ctx):
                return "hello" in ctx.message.content

            @checks.check(check_message_contains_hello)
            @bot.command()
            async def foo(ctx):
                await ctx.reply("Bar")

    See Also:
        :meth:`~.commands.Command.add_check`
    """

    def decorate(command: commands.Command) -> commands.Command:
        command.add_check(check_func)
        return command

    return decorate
