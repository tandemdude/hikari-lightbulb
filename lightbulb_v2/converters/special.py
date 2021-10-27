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
    "UserConverter",
    "MemberConverter",
    "GuildChannelConverter",
    "TextableGuildChannelConverter",
    "GuildCategoryConverter",
    "GuildVoiceChannelConverter",
    "RoleConverter",
    "EmojiConverter",
    "GuildConverter",
    "MessageConverter",
    "InviteConverter",
    "ColourConverter",
    "ColorConverter",
    "TimestampConverter",
    "SnowflakeConverter",
]

import datetime
import re
import typing as t

import hikari

from lightbulb_v2.converters import base
from lightbulb_v2.utils import search

if t.TYPE_CHECKING:
    from lightbulb_v2 import context as context_

T = t.TypeVar("T")

USER_MENTION_REGEX: t.Final[re.Pattern[str]] = re.compile(r"<@!?(\d+)>")
CHANNEL_MENTION_REGEX: t.Final[re.Pattern[str]] = re.compile(r"<#(\d+)>")
ROLE_MENTION_REGEX: t.Final[re.Pattern[str]] = re.compile(r"<@&(\d+)>")
EMOJI_MENTION_REGEX: t.Final[re.Pattern[str]] = re.compile(r"<a?:\w+:(\d+)>")
TIMESTAMP_MENTION_REGEX: t.Final[re.Pattern[str]] = re.compile(r"<t:(\d+)(?::[tTdDfFR])?>")


def _resolve_id_from_arg(arg_string: str, regex: re.Pattern[str]) -> hikari.Snowflake:
    if match := regex.match(arg_string):
        arg_string = match.group(1)
    return hikari.Snowflake(arg_string)


async def _get_or_fetch_guild_channel_from_id(
    context: context_.base.Context, channel_id: hikari.Snowflake
) -> t.Optional[hikari.GuildChannel]:
    channel = context.app.cache.get_guild_channel(channel_id)
    if channel is None:
        channel = await context.app.rest.fetch_channel(channel_id)  # type: ignore
    return channel


async def _try_convert_to_guild_channel(context: context_.base.Context, arg: str) -> t.Optional[hikari.GuildChannel]:
    if context.guild_id is None:
        raise TypeError("Cannot resolve a guild channel object for a command run outside of a guild")
    try:
        channel_id = _resolve_id_from_arg(arg, CHANNEL_MENTION_REGEX)
    except ValueError:
        channels = context.app.cache.get_guild_channels_view_for_guild(context.guild_id)
        channel = search.get(channels.values(), name=arg)
    else:
        channel = await _get_or_fetch_guild_channel_from_id(context, channel_id)
    return channel


def _raise_if_not_none(obj: t.Optional[T]) -> T:
    if obj is None:
        raise TypeError("No object could be resolved from the argument")
    return obj


class UserConverter(base.BaseConverter[hikari.User]):
    async def convert(self, arg: str) -> hikari.User:
        try:
            user_id = _resolve_id_from_arg(arg, USER_MENTION_REGEX)
        except ValueError:
            users = self.context.app.cache.get_users_view()
            user = search.find(users.values(), lambda u: u.username == arg or f"{u.username}#{u.discriminator}" == arg)
        else:
            user = self.context.app.cache.get_user(user_id)
            if user is None:
                user = await self.context.app.rest.fetch_user(user_id)
        return _raise_if_not_none(user)


class MemberConverter(base.BaseConverter[hikari.Member]):
    async def convert(self, arg: str) -> hikari.Member:
        if self.context.guild_id is None:
            raise TypeError("Cannot resolve a member object for a command run outside of a guild")
        try:
            user_id = _resolve_id_from_arg(arg, USER_MENTION_REGEX)
        except ValueError:
            members = self.context.app.cache.get_members_view_for_guild(self.context.guild_id)
            member = search.find(
                members.values(),
                lambda m: m.username == arg or m.nickname == arg or f"{m.username}#{m.discriminator}" == arg,
            )
        else:
            member = self.context.app.cache.get_member(self.context.guild_id, user_id)
            if member is None:
                member = await self.context.app.rest.fetch_member(self.context.guild_id, user_id)
        return _raise_if_not_none(member)


class GuildChannelConverter(base.BaseConverter[hikari.GuildChannel]):
    async def convert(self, arg: str) -> hikari.GuildChannel:
        channel = await _try_convert_to_guild_channel(self.context, arg)
        if not isinstance(channel, hikari.GuildChannel):
            raise TypeError("No object could be resolved from the argument")
        return channel


class TextableGuildChannelConverter(base.BaseConverter[hikari.TextableGuildChannel]):
    async def convert(self, arg: str) -> hikari.TextableGuildChannel:
        channel = await _try_convert_to_guild_channel(self.context, arg)
        if not isinstance(channel, hikari.TextableGuildChannel):
            raise TypeError("No object could be resolved from the argument")
        return channel


class GuildCategoryConverter(base.BaseConverter[hikari.GuildCategory]):
    async def convert(self, arg: str) -> hikari.GuildCategory:
        channel = await _try_convert_to_guild_channel(self.context, arg)
        if not isinstance(channel, hikari.GuildCategory):
            raise TypeError("No object could be resolved from the argument")
        return channel


class GuildVoiceChannelConverter(base.BaseConverter[hikari.GuildVoiceChannel]):
    async def convert(self, arg: str) -> hikari.GuildVoiceChannel:
        channel = await _try_convert_to_guild_channel(self.context, arg)
        if not isinstance(channel, hikari.GuildVoiceChannel):
            raise TypeError("No object could be resolved from the argument")
        return channel


class RoleConverter(base.BaseConverter[hikari.Role]):
    async def convert(self, arg: str) -> hikari.Role:
        if self.context.guild_id is None:
            raise TypeError("Cannot resolve a role object for a command run outside of a guild")
        try:
            role_id = _resolve_id_from_arg(arg, ROLE_MENTION_REGEX)
        except ValueError:
            roles = self.context.app.cache.get_roles_view_for_guild(self.context.guild_id)
            role = search.get(roles.values(), name=arg)
        else:
            role = self.context.app.cache.get_role(role_id)
            if role is None:
                fetched_roles = await self.context.app.rest.fetch_roles(self.context.guild_id)
                role = {r.id: r for r in fetched_roles}.get(role_id)
        return _raise_if_not_none(role)


class EmojiConverter(base.BaseConverter[hikari.Emoji]):
    async def convert(self, arg: str) -> hikari.Emoji:
        return hikari.Emoji.parse(arg)


class GuildConverter(base.BaseConverter[hikari.GuildPreview]):
    async def convert(self, arg: str) -> hikari.GuildPreview:
        if self.context.guild_id is None:
            raise TypeError("Cannot resolve a guild object for a command run outside of a guild")
        guild_preview = None
        if arg.isdigit():
            guild_id = int(arg)
            guild_preview = await self.context.app.rest.fetch_guild_preview(guild_id)
        else:
            guilds = self.context.app.cache.get_available_guilds_view()
            guild = search.get(guilds.values(), name=arg)
            if guild is not None:
                guild_preview = await self.context.app.rest.fetch_guild_preview(guild.id)
        return _raise_if_not_none(guild_preview)


class MessageConverter(base.BaseConverter[hikari.Message]):
    async def convert(self, arg: str) -> hikari.Message:
        try:
            m_id, c_id = int(arg), self.context.channel_id
        except ValueError:
            parts = arg.rstrip("/").split("/")
            m_id, c_id = int(parts[-1]), int(parts[-2])

        if c_id != self.context.channel_id:
            raise ValueError("Cannot convert to message for a different channel than the command was invoked in")

        return await self.context.app.rest.fetch_message(c_id, m_id)


class InviteConverter(base.BaseConverter[hikari.Invite]):
    async def convert(self, arg: str) -> hikari.Invite:
        inv_code = arg.rstrip("/").split("/")[-1]
        invite: t.Optional[hikari.Invite] = self.context.app.cache.get_invite(inv_code)
        if invite is None:
            invite = await self.context.app.rest.fetch_invite(inv_code)
        return _raise_if_not_none(invite)


class ColourConverter(base.BaseConverter[hikari.Colour]):
    async def convert(self, arg: str) -> hikari.Colour:
        return hikari.Colour.of(arg)


ColorConverter = ColourConverter


class TimestampConverter(base.BaseConverter[datetime.datetime]):
    async def convert(self, arg: str) -> datetime.datetime:
        timestamp: t.Optional[str] = None
        if match := TIMESTAMP_MENTION_REGEX.match(arg):
            timestamp = match.group(1)
        if timestamp is None:
            raise TypeError("Could not resolve timestamp")
        return datetime.datetime.fromtimestamp(int(timestamp), datetime.timezone.utc)


class SnowflakeConverter(base.BaseConverter[hikari.Snowflake]):
    async def convert(self, arg: str) -> hikari.Snowflake:
        try:
            snowflake = hikari.Snowflake(arg)
        except ValueError:
            raise TypeError("Could not resolve snowflake")
        return snowflake
