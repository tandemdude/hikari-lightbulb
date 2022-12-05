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

__all__ = ["permissions_for", "permissions_in"]

import hikari


def permissions_for(member: hikari.Member) -> hikari.Permissions:
    """
    Get the guild permissions for the given member.

    Args:
        member (:obj:`hikari.Member`): Member to get permissions for.

    Returns:
        :obj:`hikari.Permissions`: Member's guild permissions.

    Warning:
        This method relies on the cache to work. If the cache is not available then :obj:`hikari.Permissions.NONE`
        will be returned.
    """
    permissions = hikari.Permissions.NONE
    for role in member.get_roles():
        permissions |= role.permissions

    guild = member.get_guild()

    if hikari.Permissions.ADMINISTRATOR in permissions or guild and member.id == guild.owner_id:
        return hikari.Permissions.all_permissions()

    return permissions


def permissions_in(
    channel: hikari.PermissibleGuildChannel, member: hikari.Member, include_guild_permissions: bool = True
) -> hikari.Permissions:
    """
    Get the permissions for the given member in the given guild channel.

    Args:
        channel (:obj:`hikari.GuildChannel`): Channel to get the permissions in.
        member (:obj:`hikari.Member`): Member to get the permissions for.
        include_guild_permissions (:obj:`bool`): Whether or not to include the member's guild permissions. If ``False``,
            only permissions granted by overwrites will be included. Defaults to ``True``.

    Returns:
        :obj:`hikari.Permissions`: Member's permissions in the given channel.
    """
    allowed_perms = hikari.Permissions.NONE
    if include_guild_permissions:
        allowed_perms |= permissions_for(member)

    guild = member.get_guild()

    if hikari.Permissions.ADMINISTRATOR in allowed_perms or guild and member.id == guild.owner_id:
        return hikari.Permissions.all_permissions()

    overwrites = channel.permission_overwrites

    permissions = allowed_perms
    if overwrite_everyone := overwrites.get(member.guild_id):
        permissions &= ~overwrite_everyone.deny
        permissions |= overwrite_everyone.allow

    allow = hikari.Permissions.NONE
    deny = hikari.Permissions.NONE
    for role_id in member.role_ids:
        if overwrite_role := overwrites.get(role_id):
            allow |= overwrite_role.allow
            deny |= overwrite_role.deny

    permissions &= ~deny
    permissions |= allow

    if overwrite_member := overwrites.get(member.id):
        permissions &= ~overwrite_member.deny
        permissions |= overwrite_member.allow

    return permissions
