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
from __future__ import annotations

__all__ = [
    "Check",
    "owner_only",
    "guild_only",
    "dm_only",
    "bot_only",
    "webhook_only",
    "human_only",
    "nsfw_channel_only",
    "has_roles",
    "has_role_permissions",
    "has_channel_permissions",
    "has_guild_permissions",
    "bot_has_guild_permissions",
    "bot_has_role_permissions",
    "bot_has_channel_permissions",
    "has_attachments",
]

import functools
import inspect
import operator
import typing as t
import warnings

import hikari

from lightbulb import context as context_
from lightbulb import errors
from lightbulb.utils import permissions

if t.TYPE_CHECKING:
    from lightbulb import app
    from lightbulb import commands
    from lightbulb import plugins

_CallbackT = t.Union[
    t.Callable[[context_.base.Context], t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]],
    functools.partial,  # type: ignore[type-arg]
]


class _ExclusiveCheck:
    __slots__ = ("_checks",)

    def __init__(self, *checks: "Check") -> None:
        self._checks = list(checks)

    def __name__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"ExclusiveCheck({', '.join(repr(c) for c in self._checks)})"

    def __or__(self, other: t.Union["_ExclusiveCheck", "Check"]) -> "_ExclusiveCheck":
        if isinstance(other, _ExclusiveCheck):
            self._checks.extend(other._checks)
        else:
            self._checks.append(other)
        return self

    async def _evaluate(self, context: context_.base.Context) -> bool:
        failed = []

        for check in self._checks:
            try:
                res = check(context)
                if inspect.iscoroutine(res):
                    res = await res

                if not res:
                    raise errors.CheckFailure(f"Check {check.__name__!r} failed")
                return True
            except Exception as ex:
                if isinstance(ex, errors.CheckFailure) and not ex.__cause__:
                    ex = errors.CheckFailure(str(ex), causes=[ex])
                    ex.__cause__ = ex
                failed.append(ex)

        if failed:
            if len(failed) == 1:
                raise failed[0]
            raise errors.CheckFailure(
                "None of the exclusive checks passed: " + ", ".join(str(ex) for ex in failed), causes=failed
            )
        return True

    def __call__(self, context: context_.base.Context) -> t.Coroutine[t.Any, t.Any, bool]:
        return self._evaluate(context)

    def add_to_object_hook(
        self, obj: t.Union[plugins.Plugin, app.BotApp, commands.base.CommandLike]
    ) -> t.Union[plugins.Plugin, app.BotApp, commands.base.CommandLike]:
        for check in self._checks:
            check.add_to_object_hook(obj)
        return obj


class Check:
    """
    Class representing a check. Check functions can be synchronous or asynchronous functions which take
    a single argument, which will be the context that the command is being invoked under, and return
    a boolean or raise a :obj:`.errors.CheckFailure` indicating whether the check passed or failed.

    Args:
        p_callback (CallbackT): Check function to use for prefix commands.
        s_callback (Optional[CallbackT]): Check function to use for slash commands.
        m_callback (Optional[CallbackT]): Check function to use for message commands.
        u_callback (Optional[CallbackT]): Check function to use for user commands.
        add_hook (Optional[Callable[[T], T]]): Function called when the check is added to an object.
    """

    __slots__ = ("prefix_callback", "slash_callback", "message_callback", "user_callback", "add_to_object_hook")

    def __init__(
        self,
        p_callback: _CallbackT,
        s_callback: t.Optional[_CallbackT] = None,
        m_callback: t.Optional[_CallbackT] = None,
        u_callback: t.Optional[_CallbackT] = None,
        add_hook: t.Optional[
            t.Callable[
                [t.Union[plugins.Plugin, app.BotApp, commands.base.CommandLike]],
                t.Union[plugins.Plugin, app.BotApp, commands.base.CommandLike],
            ]
        ] = None,
    ) -> None:
        self.prefix_callback = p_callback
        self.slash_callback = s_callback or p_callback
        self.message_callback = m_callback or p_callback
        self.user_callback = u_callback or p_callback
        self.add_to_object_hook = add_hook or (lambda o: o)

    def __repr__(self) -> str:
        return f"Check({self.__name__.strip('_')})"

    def __or__(self, other: t.Union["Check", _ExclusiveCheck]) -> _ExclusiveCheck:
        return _ExclusiveCheck(self) | other

    @property
    def __name__(self) -> str:
        if isinstance(self.prefix_callback, functools.partial):
            return self.prefix_callback.func.__name__
        return self.prefix_callback.__name__

    def __call__(self, context: context_.base.Context) -> t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]:
        if isinstance(context, context_.prefix.PrefixContext):
            return self.prefix_callback(context)
        elif isinstance(context, context_.slash.SlashContext):
            return self.slash_callback(context)
        elif isinstance(context, context_.message.MessageContext):
            return self.message_callback(context)
        elif isinstance(context, context_.user.UserContext):
            return self.user_callback(context)
        return True


async def _owner_only(context: context_.base.Context) -> bool:
    if not context.app.owner_ids:
        context.app.owner_ids = await context.app.fetch_owner_ids()

    if context.author.id not in context.app.owner_ids:
        raise errors.NotOwner("You are not the owner of this bot")
    return True


def _guild_only(context: context_.base.Context) -> bool:
    if context.guild_id is None:
        raise errors.OnlyInGuild("This command can only be used in a guild")
    return True


def _dm_only(context: context_.base.Context) -> bool:
    if context.guild_id is not None:
        raise errors.OnlyInDM("This command can only be used in DMs")
    return True


def _bot_only(context: context_.base.Context) -> bool:
    if not context.author.is_bot:
        raise errors.BotOnly("This command can only be used by bots")
    return True


def _webhook_only(context: context_.base.Context) -> bool:
    if not isinstance(context, context_.prefix.PrefixContext):
        raise errors.WebhookOnly("This command can only be used by webhooks")
    if context.event.message.webhook_id is None:
        raise errors.WebhookOnly("This command can only be used by webhooks")
    return True


def _human_only(context: context_.base.Context) -> bool:
    if isinstance(context, context_.prefix.PrefixContext) and (
        context.author.is_bot or context.event.message.webhook_id is not None
    ):
        raise errors.HumanOnly("This command can only be used by humans")
    if context.author.is_bot:
        raise errors.HumanOnly("This command can only be used by humans")
    return True


def _nsfw_channel_only(context: context_.base.Context) -> bool:
    if context.guild_id is None:
        raise errors.NSFWChannelOnly("This command can only be used in NSFW channels")

    channel = context.get_channel()

    # Threads do not have their nsfw status attached to them,
    # they inherit that from the channel they are part of
    if isinstance(channel, hikari.GuildThreadChannel):
        channel = context.app.cache.get_guild_channel(channel.parent_id)

    assert isinstance(channel, hikari.PermissibleGuildChannel)

    if not channel.is_nsfw:
        raise errors.NSFWChannelOnly("This command can only be used in NSFW channels")
    return True


def _has_roles(
    context: context_.base.Context, *, roles: t.Sequence[int], check_func: t.Callable[[t.Sequence[bool]], bool]
) -> bool:
    _guild_only(context)
    assert context.member is not None

    missing_roles = [r for r in roles if r not in context.member.role_ids]
    # TODO: could potentially optimise any() by stopping the iteration when a required role was found
    if (check_func is all and missing_roles) or len(missing_roles) == len(roles):
        raise errors.MissingRequiredRole(
            "You are missing one or more roles required in order to run this command",
            roles=missing_roles,
            mode=check_func,
        )
    return True


def _has_guild_permissions(context: context_.base.Context, *, perms: hikari.Permissions) -> bool:
    if isinstance(context, context_.base.ApplicationContext):
        cmd = t.cast("commands.base.ApplicationCommand", context.invoked)
        if (context.guild_id is None and cmd.app_command_dm_enabled) or cmd.app_command_bypass_author_permission_checks:
            return True

    _guild_only(context)

    if isinstance(context, context_.base.ApplicationContext):
        assert context.interaction.member is not None
        missing_perms = ~context.interaction.member.permissions & perms
        if missing_perms is not hikari.Permissions.NONE:
            raise errors.MissingRequiredPermission(
                "You are missing one or more permissions required in order to run this command", perms=missing_perms
            )
        return True

    channel = context.get_channel()

    # Threads do not have permissions attached to them, they inherit that from
    # the channel they are part of
    if isinstance(channel, hikari.GuildThreadChannel):
        channel = context.app.cache.get_guild_channel(channel.parent_id)

    if channel is None:
        raise errors.InsufficientCache("Some objects required for this check could not be resolved from the cache")

    assert context.member is not None and isinstance(channel, hikari.PermissibleGuildChannel)
    missing_perms = ~permissions.permissions_in(channel, context.member) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", perms=missing_perms
        )
    return True


def _has_role_permissions(context: context_.base.Context, *, perms: hikari.Permissions) -> bool:
    if isinstance(context, context_.base.ApplicationContext):
        cmd = t.cast("commands.base.ApplicationCommand", context.invoked)
        if (context.guild_id is None and cmd.app_command_dm_enabled) or cmd.app_command_bypass_author_permission_checks:
            return True

    _guild_only(context)

    assert context.member is not None
    missing_perms = ~permissions.permissions_for(context.member) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", perms=missing_perms
        )
    return True


def _has_channel_permissions(context: context_.base.Context, *, perms: hikari.Permissions) -> bool:
    if isinstance(context, context_.base.ApplicationContext):
        cmd = t.cast("commands.base.ApplicationCommand", context.invoked)
        if (context.guild_id is None and cmd.app_command_dm_enabled) or cmd.app_command_bypass_author_permission_checks:
            return True

    _guild_only(context)

    channel = context.get_channel()

    # Threads do not have permissions attached to them, they inherit that from
    # the channel they are part of
    if isinstance(channel, hikari.GuildThreadChannel):
        channel = context.app.cache.get_guild_channel(channel.parent_id)

    if channel is None:
        raise errors.InsufficientCache("Some objects required for this check could not be resolved from the cache")

    assert context.member is not None and isinstance(channel, hikari.PermissibleGuildChannel)
    missing_perms = ~permissions.permissions_in(channel, context.member, include_guild_permissions=False) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise errors.MissingRequiredPermission(
            "You are missing one or more permissions required in order to run this command", perms=missing_perms
        )
    return True


def _bot_has_guild_permissions(context: context_.base.Context, *, perms: hikari.Permissions) -> bool:
    _guild_only(context)

    # TODO - do we need to check for dm_enabled for these checks?
    if isinstance(context, context_.base.ApplicationContext):
        assert context.interaction.app_permissions is not None
        missing_perms = ~context.interaction.app_permissions & perms
        if missing_perms is not hikari.Permissions.NONE:
            raise errors.BotMissingRequiredPermission(
                "The bot is missing one or more permissions required in order to run this command", perms=missing_perms
            )
        return True

    channel = context.get_channel()

    # Threads do not have permissions attached to them, they inherit that from
    # the channel they are part of
    if isinstance(channel, hikari.GuildThreadChannel):
        channel = context.app.cache.get_guild_channel(channel.parent_id)

    if channel is None:
        raise errors.InsufficientCache("Some objects required for this check could not be resolved from the cache")

    me = context.app.get_me()
    assert me is not None
    assert context.guild_id is not None  # Asserted above through _guild_only
    member = context.app.cache.get_member(context.guild_id, me.id)
    if member is None:
        raise errors.InsufficientCache("Some objects required for this check could not be resolved from the cache")

    assert isinstance(channel, hikari.PermissibleGuildChannel)
    missing_perms = ~permissions.permissions_in(channel, member) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise errors.BotMissingRequiredPermission(
            "The bot is missing one or more permissions required in order to run this command", perms=missing_perms
        )
    return True


def _bot_has_role_permissions(context: context_.base.Context, *, perms: hikari.Permissions) -> bool:
    _guild_only(context)

    me = context.app.get_me()
    assert me is not None
    assert context.guild_id is not None  # Asserted above through _guild_only
    member = context.app.cache.get_member(context.guild_id, me.id)
    if member is None:
        raise errors.InsufficientCache("Some objects required for this check could not be resolved from the cache")

    missing_perms = ~permissions.permissions_for(member) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise errors.BotMissingRequiredPermission(
            "The bot is missing one or more permissions required in order to run this command", perms=missing_perms
        )
    return True


def _bot_has_channel_permissions(context: context_.base.Context, *, perms: hikari.Permissions) -> bool:
    _guild_only(context)

    channel = context.get_channel()

    # Threads do not have permissions attached to them, they inherit that from
    # the channel they are part of
    if isinstance(channel, hikari.GuildThreadChannel):
        channel = context.app.cache.get_guild_channel(channel.parent_id)

    if channel is None:
        raise errors.InsufficientCache("Some objects required for this check could not be resolved from the cache")

    me = context.app.get_me()
    assert me is not None
    assert context.guild_id is not None  # Asserted above through _guild_only
    member = context.app.cache.get_member(context.guild_id, me.id)

    if member is None:
        raise errors.InsufficientCache("Some objects required for this check could not be resolved from the cache")

    assert isinstance(channel, hikari.PermissibleGuildChannel)
    missing_perms = ~permissions.permissions_in(channel, member, include_guild_permissions=False) & perms
    if missing_perms is not hikari.Permissions.NONE:
        raise errors.BotMissingRequiredPermission(
            "The bot is missing one or more permissions required in order to run this command", perms=missing_perms
        )
    return True


def _has_attachments(context: context_.base.Context, *, file_exts: t.Sequence[str] = ()) -> bool:
    if not context.attachments:
        raise errors.MissingRequiredAttachment("Missing attachment(s) required to run the command")

    if file_exts:
        for attachment in context.attachments:
            if not any(attachment.filename.endswith(ext) for ext in file_exts):
                raise errors.MissingRequiredAttachment("Missing attachment(s) required to run the command")

    return True


owner_only = Check(_owner_only)
"""Prevents a command from being used by anyone other than the owner of the application."""
guild_only = Check(_guild_only)
"""Prevents a command from being used in direct messages."""
dm_only = Check(_dm_only)
"""Prevents a command from being used in a guild."""
bot_only = Check(_bot_only)
"""Prevents a command from being used by anyone other than a bot."""
webhook_only = Check(_webhook_only)
"""Prevents a command from being used by anyone other than a webhook."""
human_only = Check(_human_only)
"""Prevents a command from being used by anyone other than a human."""
nsfw_channel_only = Check(_nsfw_channel_only)
"""
Prevents a command from being used in any channel other than one marked as NSFW.

.. deprecated:: 2.3.1
    Use the ``nsfw`` kwarg in the :obj:`~lightbulb.decorators.command` decorator instead. This will be removed
    in version ``2.4.0``.
"""


def has_roles(role1: int, *roles: int, mode: t.Callable[[t.Sequence[bool]], bool] = all) -> Check:
    """
    Prevents a command from being used by anyone missing roles according to the given mode.
    This check supports slash commands.

    Args:
        role1 (:obj:`int`): Role ID to check for.
        *roles (:obj:`int`): Additional role IDs to check for.

    Keyword Args:
        mode (``all`` or ``any``): The mode to check roles using. If ``all``, all role IDs passed will
            be required. If ``any``, only one of the role IDs will be required. Defaults to ``all``.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have roles
        in a DM channel.
    """
    if mode not in (any, all):
        raise TypeError("mode must be one of: any, all")
    return Check(functools.partial(_has_roles, roles=[role1, *roles], check_func=mode))


def has_guild_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> Check:
    """
    Prevents the command from being used by a member missing any of the required
    permissions (this takes into account permissions granted by both roles and permission overwrites).

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *perms (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return Check(functools.partial(_has_guild_permissions, perms=reduced))


def has_role_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> Check:
    """
    Prevents the command from being used by a member missing any of the required role
    permissions.

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *perms (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return Check(functools.partial(_has_role_permissions, perms=reduced))


def has_channel_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> Check:
    """
    Prevents the command from being used by a member missing any of the required
    channel permissions (permissions granted by a permission overwrite).

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *perms (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return Check(functools.partial(_has_channel_permissions, perms=reduced))


def bot_has_guild_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> Check:
    """
    Prevents the command from being used if the bot is missing any of the required
    permissions (this takes into account permissions granted by both roles and permission overwrites).

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *perms (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return Check(functools.partial(_bot_has_guild_permissions, perms=reduced))


def bot_has_role_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> Check:
    """
    Prevents the command from being used if the bot is missing any of the required role
    permissions.

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *perms (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return Check(functools.partial(_bot_has_role_permissions, perms=reduced))


def bot_has_channel_permissions(perm1: hikari.Permissions, *perms: hikari.Permissions) -> Check:
    """
    Prevents the command from being used if the bot is missing any of the required channel
    permissions (permissions granted a permission overwrite).

    Args:
        perm1 (:obj:`hikari.Permissions`): Permission to check for.
        *perms (:obj:`hikari.Permissions`): Additional permissions to check for.

    Note:
        This check will also prevent commands from being used in DMs, as you cannot have permissions
        in a DM channel.

    Warning:
        This check is unavailable if your application is stateless and/or missing the intent
        :obj:`hikari.Intents.GUILDS` and will **always** raise an error on command invocation if
        either of these conditions are not met.
    """
    reduced = functools.reduce(operator.or_, [perm1, *perms])
    return Check(functools.partial(_bot_has_channel_permissions, perms=reduced))


def has_attachments(*extensions: str) -> Check:
    """
    Prevents the command from being used if the invocation message
    does not include any attachments.

    Args:
        *extensions (:obj:`str`): If specified, attachments with different file extensions
            will cause the check to fail.

    Note:
        If ``extensions`` is specified then all attachments must conform to the restriction.
    """
    warnings.warn(
        "'has_attachments' is deprecated and scheduled for removal in version '2.5.0'. "
        "Use an option with type 'hikari.Attachment' instead.",
        DeprecationWarning,
    )
    return Check(functools.partial(_has_attachments, file_exts=extensions))
