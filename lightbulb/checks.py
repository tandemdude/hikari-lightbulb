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
from __future__ import annotations

__all__: typing.Final[typing.List[str]] = [
    "guild_only",
    "dm_only",
    "owner_only",
    "bot_only",
    "human_only",
    "has_roles",
    "check",
]

import typing
import functools

from lightbulb import context
from lightbulb import commands
from lightbulb import errors

if typing.TYPE_CHECKING:
    import hikari
    from hikari.utilities import snowflake

T_inv = typing.TypeVar("T_inv", bound=commands.Command)


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


async def _bot_only(ctx: context.Context) -> bool:
    if not ctx.author.is_bot:
        raise errors.BotOnly(f"Only a bot can use {ctx.invoked_with}")
    return True


async def _human_only(ctx: context.Context) -> bool:
    if ctx.author.is_bot:
        raise errors.HumanOnly(f"Only an human can use {ctx.invoked_with}")
    return True


def _role_check(member_roles: typing.Sequence[hikari.Snowflake], *, roles: typing.Sequence[int], func) -> bool:
    return func(r in member_roles for r in roles)


async def _has_roles(ctx: context.Context, *, role_check):
    await _guild_only(ctx)
    if not role_check(ctx.member.role_ids):
        raise errors.MissingRequiredRole("You are missing one or more roles required in order to run this command.")
    return True


def guild_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used in direct messages.
    """

    def decorate(command: T_inv) -> T_inv:
        command.add_check(_guild_only)
        return command

    return decorate


def dm_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used in a guild.

    Example:

        .. code-block:: python

            @lightbulb.dm_only()
            @bot.command()
            async def foo(ctx):
                await ctx.reply("bar")
    """

    def decorate(command: T_inv) -> T_inv:
        command.add_check(_dm_only)
        return command

    return decorate


def owner_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used by anyone other than the owner of the application.
    """

    def decorate(command: T_inv) -> T_inv:
        command.add_check(_owner_only)
        return command

    return decorate


def bot_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used by anyone other than a bot.
    """

    def decorate(command: T_inv) -> T_inv:
        command.add_check(_bot_only)
        return command

    return decorate


def human_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used by anyone other than a human.
    """

    def decorate(command: T_inv) -> T_inv:
        command.add_check(_human_only)
        return command

    return decorate


def has_roles(
    role1: snowflake.SnowflakeishOr[hikari.PartialRole],
    *role_ids: snowflake.SnowflakeishOr[hikari.PartialRole],
    mode: typing.Literal["all", "any"] = "all",
):
    """
    A decorator that prevents a command from being used by anyone missing roles according
    to the given mode.

    Args:
        role1 (:obj:`~hikari.utilities.snowflake.SnowflakeishOr` [ :obj:`~hikari.PartialRole` ]): Role ID to check for.
        *role_ids (:obj:`~hikari.utilities.snowflake.SnowflakeishOr` [ :obj:`~hikari.PartialRole` ]): Additional role IDs to check for.

    Keyword Args:
        mode (Literal["all", "any"]): The mode to check roles using. If ``"all"``, all role IDs
            passed will be required. If ``"any"``, the invoker will only be required to have one
            of the specified roles. Defaults to ``"all"``.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have roles
        in a DM channel.
    """
    if mode not in ["all", "any"]:
        raise SyntaxError("has_roles mode must be one of: all, any")

    def decorate(command: T_inv) -> T_inv:
        check_func = functools.partial(
            _role_check, roles=[int(role1), *[int(r) for r in role_ids]], func=all if mode == "all" else any
        )
        command.add_check(functools.partial(_has_roles, role_check=check_func))
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

    def decorate(command: T_inv) -> T_inv:
        command.add_check(check_func)
        return command

    return decorate
