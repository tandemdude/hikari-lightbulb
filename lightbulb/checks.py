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
"""
.. error::
    Note that all check decorators **must** be above the command decorator otherwise your code will not work.
"""
from __future__ import annotations

__all__: typing.Final[typing.List[str]] = [
    "dm_only",
    "guild_only",
    "owner_only",
    "bot_only",
    "human_only",
    "has_roles",
    "has_guild_permissions",
    "bot_has_guild_permissions",
    "check",
]

import functools
import types
import typing

import hikari

from lightbulb import commands
from lightbulb import context
from lightbulb import errors

if typing.TYPE_CHECKING:
    from hikari import snowflakes

T_inv = typing.TypeVar("T_inv", bound=commands.Command)

_CHECK_DECORATOR_BELOW_COMMAND_DECORATOR_MESSAGE = """Check decorators MUST be above the commands decorator in order for them to work.

Valid:

@lightbulb.guild_only()
@lightbulb.command()
async def foo(ctx):
    ...

Invalid:

@lightbulb.command()
@lightbulb.guild_only()
async def foo(ctx):
    ...

See https://tandemdude.gitlab.io/lightbulb/api-reference.html#module-lightbulb.checks
"""


def _check_check_decorator_above_commands_decorator(func_or_command) -> None:
    if isinstance(func_or_command, types.FunctionType):
        raise SyntaxError(_CHECK_DECORATOR_BELOW_COMMAND_DECORATOR_MESSAGE)


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


def _get_missing_perms(
    permissions: typing.Sequence[hikari.Permissions], roles: typing.Sequence[hikari.Role]
) -> typing.Sequence[hikari.Permissions]:
    missing_perms = []
    for perm in permissions:
        if not any(role.permissions & perm for role in roles):
            missing_perms.append(perm)
    return missing_perms


async def _has_guild_permissions(ctx: context.Context, *, permissions: typing.Sequence[hikari.Permissions]):
    if ctx.bot.is_stateless:
        raise NotImplementedError("The bot is stateless. Cache operations are not available")
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    roles = ctx.bot.cache.get_roles_view_for_guild(ctx.guild_id).values()
    missing_perms = _get_missing_perms(permissions, [role for role in roles if role.id in ctx.member.role_ids])

    if missing_perms:
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", permissions=missing_perms
        )
    return True


async def _bot_has_guild_permissions(ctx: context.Context, *, permissions: typing.Sequence[hikari.Permissions]):
    if ctx.bot.is_stateless:
        raise NotImplementedError("The bot is stateless. Cache operations are not available")
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    roles = ctx.bot.cache.get_roles_view_for_guild(ctx.guild_id).values()
    bot_member = ctx.bot.cache.get_member(ctx.guild_id, ctx.bot.cache.get_me().id)
    missing_perms = _get_missing_perms(permissions, [role for role in roles if role.id in bot_member.role_ids])

    if missing_perms:
        raise errors.BotMissingRequiredPermission(
            "I am missing one or more permissions required in order to run this command", permissions=missing_perms
        )
    return True


def guild_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used in direct messages.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
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
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(_dm_only)
        return command

    return decorate


def owner_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used by anyone other than the owner of the application.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(_owner_only)
        return command

    return decorate


def bot_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used by anyone other than a bot.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(_bot_only)
        return command

    return decorate


def human_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used by anyone other than a human.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(_human_only)
        return command

    return decorate


def has_roles(
    role1: snowflakes.SnowflakeishOr[hikari.PartialRole],
    *role_ids: snowflakes.SnowflakeishOr[hikari.PartialRole],
    mode: typing.Literal["all", "any"] = "all",
):
    """
    A decorator that prevents a command from being used by anyone missing roles according
    to the given mode.

    Args:
        role1 (:obj:`~hikari.snowflakes.SnowflakeishOr` [ :obj:`~hikari.PartialRole` ]): Role ID to check for.
        *role_ids (:obj:`~hikari.snowflakes.SnowflakeishOr` [ :obj:`~hikari.PartialRole` ]): Additional role IDs to check for.

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
        _check_check_decorator_above_commands_decorator(command)
        check_func = functools.partial(
            _role_check, roles=[int(role1), *[int(r) for r in role_ids]], func=all if mode == "all" else any
        )
        command.add_check(functools.partial(_has_roles, role_check=check_func))
        return command

    return decorate


def has_guild_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    A decorator that prevents the command from being used by a member missing any of the required
    guild permissions (permissions granted by a role).

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *permissions (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        perms = set(perm1.split())
        for permission in permissions:
            for perm in permission.split():
                perms.add(perm)
        for perm in perms:
            command.user_required_permissions.add(perm)
        command.add_check(functools.partial(_has_guild_permissions, permissions=list(perms)))
        return command

    return decorate


def bot_has_guild_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    A decorator that prevents the command from being used if the bot is missing any of the required
    guild permissions (permissions granted by a role).

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *permissions (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        perms = set(perm1.split())
        for permission in permissions:
            for perm in permission.split():
                perms.add(perm)
        for perm in perms:
            command.bot_required_permissions.add(perm)
        command.add_check(functools.partial(_bot_has_guild_permissions, permissions=list(perms)))
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
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(check_func)
        return command

    return decorate
