# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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
    "webhook_only",
    "human_only",
    "has_roles",
    "has_guild_permissions",
    "bot_has_guild_permissions",
    "has_role_permissions",
    "bot_has_role_permissions",
    "has_channel_permissions",
    "bot_has_channel_permissions",
    "has_permissions",
    "bot_has_permissions",
    "has_attachment",
    "check",
    "check_exempt",
]

import functools
import inspect
import operator
import typing
import warnings

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

See https://hikari-lightbulb.readthedocs.io/en/latest/api-reference.html#module-lightbulb.checks
"""


def _check_check_decorator_above_commands_decorator(func_or_command) -> None:
    if inspect.isfunction(func_or_command) or inspect.ismethod(func_or_command):
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


async def _webhook_only(ctx: context.Context) -> bool:
    if ctx.message.webhook_id is None:
        raise errors.WebhookOnly(f"Only a webhook can use {ctx.invoked_with}")
    return True


async def _human_only(ctx: context.Context) -> bool:
    if ctx.author.is_bot or ctx.message.webhook_id is not None:
        raise errors.HumanOnly(f"Only an human can use {ctx.invoked_with}")
    return True


async def _nsfw_channel_only(ctx: context.Context) -> bool:
    if not ctx.get_channel().is_nsfw:
        raise errors.NSFWChannelOnly(f"{ctx.invoked_with} can only be used in an NSFW channel")
    return True


def _role_check(member_roles: typing.Sequence[hikari.Snowflake], *, roles: typing.Sequence[int], func) -> bool:
    return func(r in member_roles for r in roles)


async def _has_roles(ctx: context.Context, *, role_check):
    await _guild_only(ctx)
    if not role_check(ctx.member.role_ids):
        raise errors.MissingRequiredRole("You are missing one or more roles required in order to run this command.")
    return True


def _get_missing_permissions(
    required_permissions: hikari.Permissions, user_permissions: hikari.Permissions
) -> hikari.Permissions:
    if hikari.Permissions.ADMINISTRATOR & user_permissions:
        return hikari.Permissions.NONE

    missing_perms = required_permissions & ~user_permissions

    return missing_perms


async def _has_guild_permissions(ctx: context.Context, *, permissions: hikari.Permissions) -> bool:
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    member = ctx.member
    if ctx.get_guild().owner_id == member.id:
        return True

    _user_role_perms = hikari.Permissions.NONE
    for role in member.get_roles():
        _user_role_perms |= role.permissions

    if _user_role_perms & hikari.Permissions.ADMINISTRATOR:
        return True

    perm_over = ctx.get_channel().permission_overwrites.values()

    _user_denies = _user_allows = _role_denies = _role_allows = denied_perms = allowed_perms = hikari.Permissions.NONE

    for override in perm_over:
        _user_denies |= override.deny if override.id == member.id else hikari.Permissions.NONE
        _user_allows |= override.allow if override.id == member.id else hikari.Permissions.NONE

        _role_denies |= override.deny if override.id in member.role_ids else hikari.Permissions.NONE
        _role_allows |= override.allow if override.id in member.role_ids else hikari.Permissions.NONE

    denied_perms |= _user_denies | (_role_denies & ~_user_allows)
    allowed_perms |= _user_allows | (_role_allows & ~_user_denies)

    allowed_perms |= _user_role_perms & ~denied_perms
    denied_perms |= ~allowed_perms

    if denied_and_needed := (permissions & denied_perms):
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", denied_and_needed
        )
    return True


async def _bot_has_guild_permissions(ctx: context.Context, *, permissions: hikari.Permissions) -> bool:
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    member = ctx.get_guild().get_member(ctx.bot.get_me())

    if ctx.get_guild().owner_id == member.id:
        return True

    _user_role_perms = hikari.Permissions.NONE
    for role in member.get_roles():
        _user_role_perms |= role.permissions

    if _user_role_perms & hikari.Permissions.ADMINISTRATOR:
        return True

    perm_over = ctx.get_channel().permission_overwrites.values()

    _user_denies = _user_allows = _role_denies = _role_allows = denied_perms = allowed_perms = hikari.Permissions.NONE

    for override in perm_over:
        _user_denies |= override.deny if override.id == member.id else hikari.Permissions.NONE
        _user_allows |= override.allow if override.id == member.id else hikari.Permissions.NONE

        _role_denies |= override.deny if override.id in member.role_ids else hikari.Permissions.NONE
        _role_allows |= override.allow if override.id in member.role_ids else hikari.Permissions.NONE

    denied_perms |= _user_denies | (_role_denies & ~_user_allows)
    allowed_perms |= _user_allows | (_role_allows & ~_user_denies)

    allowed_perms |= _user_role_perms & ~denied_perms
    denied_perms |= ~allowed_perms

    if denied_and_needed := (permissions & denied_perms):
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", denied_and_needed
        )
    return True


async def _has_role_permissions(ctx: context.Context, *, permissions: hikari.Permissions) -> bool:
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    if ctx.get_guild().owner_id == ctx.author.id:
        return True

    user_perms = hikari.Permissions.NONE
    for role in ctx.member.get_roles():
        user_perms |= role.permissions

    if user_perms & hikari.Permissions.ADMINISTRATOR:
        return True

    if missing_perms := (permissions & ~user_perms):
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", missing_perms
        )
    return True


async def _bot_has_role_permissions(ctx: context.Context, *, permissions: hikari.Permissions) -> bool:
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    bot_member = ctx.get_guild().get_member(ctx.bot.get_me())
    if ctx.get_guild().owner_id == bot_member.id:
        return True

    user_perms = hikari.Permissions.NONE
    for role in bot_member.get_roles():
        user_perms |= role.permissions

    if user_perms & hikari.Permissions.ADMINISTRATOR:
        return True

    if missing_perms := (permissions & ~user_perms):
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", missing_perms
        )
    return True


async def _has_channel_permissions(ctx: context.Context, *, permissions: hikari.Permissions) -> bool:
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    member = ctx.member
    if ctx.get_guild().owner_id == member.id:
        return True

    perm_over = ctx.get_channel().permission_overwrites.values()

    _user_denies = _user_allows = _role_denies = _role_allows = denied_perms = allowed_perms = hikari.Permissions.NONE

    for override in perm_over:
        _user_denies |= override.deny if override.id == member.id else hikari.Permissions.NONE
        _user_allows |= override.allow if override.id == member.id else hikari.Permissions.NONE

        _role_denies |= override.deny if override.id in member.role_ids else hikari.Permissions.NONE
        _role_allows |= override.allow if override.id in member.role_ids else hikari.Permissions.NONE

    denied_perms |= _user_denies | (_role_denies & ~_user_allows)
    allowed_perms |= _user_allows | (_role_allows & ~_user_denies)

    if not (permissions & ~allowed_perms):
        return True

    raise errors.MissingRequiredPermission(
        "You are missing one or more permissions required in order to run this command", permissions & ~allowed_perms
    )


async def _bot_has_channel_permissions(ctx: context.Context, *, permissions: hikari.Permissions) -> bool:
    if not (ctx.bot.intents & hikari.Intents.GUILDS) == hikari.Intents.GUILDS:
        raise hikari.MissingIntentError(hikari.Intents.GUILDS)

    await _guild_only(ctx)

    member = ctx.get_guild().get_member(ctx.bot.get_me())
    if ctx.get_guild().owner_id == member.id:
        return True

    perm_over = ctx.get_channel().permission_overwrites.values()

    _user_denies = _user_allows = _role_denies = _role_allows = denied_perms = allowed_perms = hikari.Permissions.NONE

    for override in perm_over:
        _user_denies |= override.deny if override.id == member.id else hikari.Permissions.NONE
        _user_allows |= override.allow if override.id == member.id else hikari.Permissions.NONE

        _role_denies |= override.deny if override.id in member.role_ids else hikari.Permissions.NONE
        _role_allows |= override.allow if override.id in member.role_ids else hikari.Permissions.NONE

    denied_perms |= _user_denies | (_role_denies & ~_user_allows)
    allowed_perms |= _user_allows | (_role_allows & ~_user_denies)

    if not (permissions & ~allowed_perms):
        return True

    raise errors.MissingRequiredPermission(
        "You are missing one or more permissions required in order to run this command", permissions & ~allowed_perms
    )


async def _has_attachment(
    ctx: context.Context, *, allowed_extensions: typing.Optional[typing.Sequence[str]] = None
) -> bool:
    if not ctx.attachments:
        raise errors.MissingRequiredAttachment("Missing attachment(s) required to run the command")

    if allowed_extensions is not None:
        for attachment in ctx.attachments:
            if not any(attachment.filename.endswith(ext) for ext in allowed_extensions):
                raise errors.MissingRequiredAttachment("Missing attachment(s) required to run the command")

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
                await ctx.respond("bar")
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


def webhook_only() -> typing.Callable[[T_inv], T_inv]:
    """
    A decorator that prevents a command from being used by anyone other than a webhook.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(_webhook_only)
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


def nsfw_channel_only() -> typing.Callable[[T_inv], T_inv]:
    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(_nsfw_channel_only)
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
    guild permissions (this takes into account both role permissions and channel overwrites,
    where channel overwrites take priority).

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
        perms = perm1.split()

        total_perms = functools.reduce(operator.or_, (*perms, *permissions))
        command.user_required_permissions = total_perms

        command.add_check(functools.partial(_has_guild_permissions, permissions=total_perms))
        return command

    return decorate


def bot_has_guild_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    A decorator that prevents the command from being used if the bot is missing any of the required
    guild permissions (this takes into account both role permissions and channel overwrites).

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
        perms = perm1.split()

        total_perms = functools.reduce(operator.or_, (*perms, *permissions))
        command.bot_required_permissions = total_perms

        command.add_check(functools.partial(_bot_has_guild_permissions, permissions=total_perms))
        return command

    return decorate


def has_role_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    A decorator that prevents the command from being used by a member missing any of the required
    role permissions.

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
        perms = perm1.split()

        total_perms = functools.reduce(operator.or_, (*perms, *permissions))
        command.user_required_permissions = total_perms

        command.add_check(functools.partial(_has_role_permissions, permissions=total_perms))
        return command

    return decorate


def bot_has_role_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    A decorator that prevents the command from being used if the bot is missing any of the required
    role permissions.

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
        perms = perm1.split()

        total_perms = functools.reduce(operator.or_, (*perms, *permissions))
        command.user_required_permissions = total_perms

        command.add_check(functools.partial(_bot_has_role_permissions, permissions=total_perms))
        return command

    return decorate


def has_channel_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    A decorator that prevents the command from being used by a member missing any of the required
    channel permissions (permissions granted by a permission overwrite).

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
        perms = perm1.split()

        total_perms = functools.reduce(operator.or_, (*perms, *permissions))
        command.user_required_permissions = total_perms

        command.add_check(functools.partial(_has_channel_permissions, permissions=total_perms))
        return command

    return decorate


def bot_has_channel_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    A decorator that prevents the command from being used if the bot is missing any of the required
    channel permissions (permissions granted by a permission overwrite).

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
        perms = perm1.split()

        total_perms = functools.reduce(operator.or_, (*perms, *permissions))
        command.user_required_permissions = total_perms

        command.add_check(functools.partial(_bot_has_channel_permissions, permissions=total_perms))
        return command

    return decorate


def has_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    Alias for :obj:`~has_channel_permissions` for backwards compatibility.

    This is deprecated, use :obj:`~has_channel_permissions` instead.
    """
    warnings.warn(
        "The permissions check 'has_permissions' is deprecated and scheduled for removal in version 1.4. "
        "You should use 'has_channel_permissions' instead.",
        DeprecationWarning,
    )
    return has_channel_permissions(perm1, *permissions)


def bot_has_permissions(perm1: hikari.Permissions, *permissions: hikari.Permissions):
    """
    Alias for :obj:`~bot_has_channel_permissions` for backwards compatibility.

    This is deprecated, use :obj:`~bot_has_channel_permissions` instead.
    """
    warnings.warn(
        "The permissions check 'bot_has_permissions' is deprecated and scheduled for removal in version 1.4. "
        "You should use 'bot_has_channel_permissions' instead.",
        DeprecationWarning,
    )
    return bot_has_channel_permissions(perm1, *permissions)


def has_attachment(*extensions: str):
    """
    A decorator that prevents the command from being used if the invocation message
    does not include any attachments.

    Args:
        *extensions (:obj:`str`): If specified, attachments with a different file extension
            will cause the check to fail.

    Example:

        .. code-block:: python

            @checks.has_attachment(".yaml", ".json")
            @bot.command()
            async def foobar(ctx):
                print(ctx.attachments[0].filename)

    Note:
        If ``extensions`` is specified then all attachments must conform to the restriction.
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(functools.partial(_has_attachment, allowed_extensions=extensions if extensions else None))
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
                await ctx.respond("Bar")

    See Also:
        :meth:`~.commands.Command.add_check`
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command.add_check(check_func)
        return command

    return decorate


def check_exempt(predicate):
    """
    A decorator which allows **all** checks to be bypassed if the ``predicate`` conditions are met.
    Predicate can be a coroutine or a normal function but must take a single
    argument - ``context`` - and must return a boolean - ``True`` if checks should be bypassed or ``False`` if not.

    Args:
        predicate: The callable which determines if command checks should be bypassed or not.

    Example:

        .. code-block:: python

            @checks.check_exempt(lambda ctx: ctx.author.id == 1234)
            @checks.guild_only()
            @bot.command()
            async def foo(ctx):
                await ctx.respond("foo")
    """

    def decorate(command: T_inv) -> T_inv:
        _check_check_decorator_above_commands_decorator(command)
        command._check_exempt_predicate = predicate
        return command

    return decorate
