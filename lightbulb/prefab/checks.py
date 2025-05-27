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
__all__ = [
    "BotMissingRequiredPermissions",
    "MissingRequiredPermission",
    "MissingRequiredRoles",
    "NotOwner",
    "bot_has_permissions",
    "has_permissions",
    "has_roles",
    "owner_only",
]

import typing as t
from collections.abc import Iterable
from collections.abc import Sequence

import hikari

from lightbulb import context
from lightbulb.commands import execution


class NotOwner(Exception):
    """Exception raised when a user that does not own the bot attempts to invoke a protected command."""


@execution.hook(execution.ExecutionSteps.CHECKS, skip_when_failed=True, name="owner_only")
async def owner_only(_: execution.ExecutionPipeline, ctx: context.Context) -> None:
    """
    Hook that checks whether the user invoking the command is an owner of the bot. This takes into account
    both the owner and the team that owns the bot's application. Raises :obj:`~NotOwner` when it fails. This hook is
    run during the ``CHECKS`` execution step.
    """
    if ctx.client._owner_ids is None:
        owner_ids: set[hikari.Snowflakeish] = set()

        app = await ctx.client._ensure_application()

        owner_ids.add(app.owner.id)
        if app.team is not None:
            owner_ids.update(app.team.members.keys())
        ctx.client._owner_ids = owner_ids

    if ctx.user.id not in ctx.client._owner_ids:
        raise NotOwner


class MissingRequiredPermission(Exception):
    """Exception raised when the user invoking the command is missing one or more required permissions."""

    def __init__(self, missing: hikari.Permissions, actual: hikari.Permissions) -> None:
        self.missing: hikari.Permissions = missing
        """The permissions the user is missing."""
        self.actual: hikari.Permissions = actual
        """The permissions the user has."""


def has_permissions(
    permissions: hikari.Permissions, /, *, fail_in_dm: bool = True, permit_admin: bool = True
) -> execution.ExecutionHook:
    """
    Creates a hook that checks whether the user invoking the command has all the given permissions. The created hook
    raises :obj:`~MissingRequiredPermissions` when it fails. This hook is run during the ``CHECKS`` execution step.

    Args:
        permissions: The permissions that the user should have.
        fail_in_dm: Whether this hook should fail if the command is invoked within a DM. Defaults to :obj:`True`.
        permit_admin: Whether this hook should pass if the user has the ``ADMINISTRATOR`` permission.
            Defaults to :obj:`True`.

    Returns:
        The created hook.

    Example:

        .. code-block:: python

            class YourCommand(
                ...,
                hooks=[lightbulb.prefab.has_permissions(hikari.Permissions.ADMINISTRATOR)]
            ):
                ...
    """

    @execution.hook(execution.ExecutionSteps.CHECKS, skip_when_failed=True, name="has_permissions")
    def _has_permissions(_: execution.ExecutionPipeline, ctx: context.Context) -> None:
        if ctx.member is None:
            if fail_in_dm:
                raise MissingRequiredPermission(permissions, hikari.Permissions.NONE)
            return

        if permit_admin and (ctx.member.permissions & hikari.Permissions.ADMINISTRATOR):
            return

        if (ctx.member.permissions & permissions) != permissions:
            raise MissingRequiredPermission(permissions & ~ctx.member.permissions, ctx.member.permissions)

    return _has_permissions


class BotMissingRequiredPermissions(Exception):
    """Exception raised when the bot is missing one or more required permissions."""

    def __init__(self, missing: hikari.Permissions, actual: hikari.Permissions) -> None:
        self.missing: hikari.Permissions = missing
        """The permissions the bot is missing."""
        self.actual: hikari.Permissions = actual
        """The permissions the bot has."""


def bot_has_permissions(
    permissions: hikari.Permissions, /, *, fail_in_dm: bool = True, permit_admin: bool = True
) -> execution.ExecutionHook:
    """
    Creates a hook that checks whether the bot has all the given permissions. The created hook raises
    :obj:`~BotMissingRequiredPermissions` when it fails. This hook is run during the ``CHECKS`` execution step.

    Args:
        permissions: The permissions that the bot should have.
        fail_in_dm: Whether this hook should fail if the command is invoked within a DM. Defaults to :obj:`True`.
        permit_admin: Whether this hook should pass if the user has the ``ADMINISTRATOR`` permission.
            Defaults to :obj:`True`.

    Returns:
        The created hook.

    Example:

        .. code-block:: python

            class YourCommand(
                ...,
                hooks=[lightbulb.prefab.bot_has_permissions(hikari.Permissions.ADMINISTRATOR)]
            ):
                ...
    """

    @execution.hook(execution.ExecutionSteps.CHECKS, skip_when_failed=True, name="bot_has_permissions")
    def _bot_has_permissions(_: execution.ExecutionPipeline, ctx: context.Context) -> None:
        if ctx.guild_id is None:
            if fail_in_dm:
                raise BotMissingRequiredPermissions(permissions, hikari.Permissions.NONE)
            return

        if permit_admin and (ctx.interaction.app_permissions & hikari.Permissions.ADMINISTRATOR):
            return

        if (ctx.interaction.app_permissions & permissions) != permissions:
            raise BotMissingRequiredPermissions(
                permissions & ~ctx.interaction.app_permissions, ctx.interaction.app_permissions
            )

    return _bot_has_permissions


class MissingRequiredRoles(Exception):
    """Exception raised when the user invoking the command is missing one or more required roles."""

    def __init__(self, role_ids: Sequence[hikari.Snowflakeish]) -> None:
        self.role_ids: Sequence[hikari.Snowflakeish] = role_ids
        """The IDs of the roles the user is missing."""


def has_roles(
    *role_ids: hikari.Snowflakeish | Iterable[hikari.Snowflakeish],
    mode: t.Literal["all", "any"] = "all",
    fail_in_dm: bool = True,
) -> execution.ExecutionHook:
    """
    Creates a hook that checks whether the user invoking the command has a correct subset of the given roles.

    Args:
        *role_ids: The IDs of the role(s) that the user should have.
        mode: Whether the user is required to have all the given roles, or any subset of them.
        fail_in_dm: Whether this hook should fail if the command is invoked within a DM. Defaults to :obj:`True`.

    Returns:
        The created hook.

    Example:

        .. code-block:: python

            class YourCommand(
                ...,
                hooks=[lightbulb.prefab.has_roles(123, 456, 789, mode="any")]
            ):
                ...
    """
    flattened_role_ids = [elem for item in role_ids for elem in (item if isinstance(item, Iterable) else [item])]

    @execution.hook(execution.ExecutionSteps.CHECKS, skip_when_failed=True, name="has_roles")
    def _has_roles(_: execution.ExecutionPipeline, ctx: context.Context) -> None:
        if ctx.member is None:
            if fail_in_dm:
                raise MissingRequiredRoles(flattened_role_ids)
            return

        missing = set(flattened_role_ids).difference(ctx.member.role_ids)
        if mode == "all" and missing:
            raise MissingRequiredRoles(list(missing))
        elif mode == "any" and len(missing) == len(role_ids):
            raise MissingRequiredRoles(flattened_role_ids)

    return _has_roles
