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
Lightbulb will attempt to convert command arguments using the type or function specified by the type
hints of each argument. By default, any types that can be converted to from a string are supported - eg int or
float.

Example:
::

    @bot.command()
    async def to_int(ctx, number: int):
        await ctx.reply(f"{number}, {type(number)}")
        # If ran with the argument "10"
        # The output would be: 10, <class 'int'>

Supplied in this module are further utility functions that can be specified as type hints in order
to convert arguments into more complex types - eg member or channel objects.

You can also write your own converters. A converter can be any callable and should take a single argument, which
will be an instance of the :obj:`~lightbulb.converters.WrappedArg` class. The arg value and command invocation
context can be accessed through this instance from the attributes ``data`` and ``context`` respectively.

.. warning:: For the supplied converters, some functionality will not be possible depending on the intents and/or
    cache settings of your bot application and object. If the bot does not have a cache then the converters can
    only work for arguments of ID or mention and **not** any form of name.

.. warning:: If you use ``from __future__ import annotations`` then you **will not** be able to use converters
    in your commands. Instead of converting the arguments, the raw, unconverted arguments will be passed back
    to the command.
"""
from __future__ import annotations

__all__: typing.Final[typing.List[str]] = [
    "WrappedArg",
    "user_converter",
    "member_converter",
    "text_channel_converter",
    "guild_voice_channel_converter",
    "category_converter",
    "role_converter",
    "custom_emoji_converter",
]

import collections
import re
import typing
import warnings

import hikari

from lightbulb import context as context_
from lightbulb import errors
from lightbulb import utils

T = typing.TypeVar("T")

USER_MENTION_REGEX: typing.Final[typing.Pattern] = re.compile(r"<@!?(\d+)>")
CHANNEL_MENTION_REGEX: typing.Final[typing.Pattern] = re.compile(r"<#(\d+)>")
ROLE_MENTION_REGEX: typing.Final[typing.Pattern] = re.compile(r"<@&(\d+)>")
EMOJI_MENTION_REGEX: typing.Final[typing.Pattern] = re.compile(r"<a?:\w+:(\d+)>")


class WrappedArg(collections.UserString):
    """
    A wrapped command argument containing the invocation context
    of the command for which the argument is to be converted under, accessible
    through the :attr:`context` attribute.

    This class acts like a string so any operations that will work on a string will
    also work on this class.

    The raw string argument can be accessed through the :attr:`data` attribute.

    Args:
        seq (:obj:`str`): The argument text.
        context (:obj:`~.context.Context`): The command invocation context for the argument.
    """

    __slots__ = ["context"]

    def __init__(self, seq: str, context: context_.Context) -> None:
        super().__init__(seq)
        self.context: context_.Context = context


def _resolve_id_from_arg(arg_string: str, regex: typing.Pattern) -> hikari.Snowflake:
    if match := regex.match(arg_string):
        arg_string = match.group(1)
    return hikari.Snowflake(arg_string)


async def _get_or_fetch_guild_channel_from_id(arg: WrappedArg, channel_id: hikari.Snowflake) -> hikari.GuildChannel:
    channel = arg.context.bot.cache.get_guild_channel(channel_id)
    if channel is None:
        channel = await arg.context.bot.rest.fetch_channel(channel_id)
    return channel


def _raise_if_not_none(obj: typing.Optional[T]) -> T:
    if obj is None:
        raise errors.ConverterFailure()
    return obj


async def user_converter(arg: WrappedArg) -> hikari.User:
    """
    Converter to transform a command argument into a :obj:`hikari.UserImpl` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`hikari.UserImpl`: The user object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a user object.

    Example:

        .. code-block:: python

            @bot.command()
            async def username(ctx, user: lightbulb.converters.user_converter):
                await ctx.reply(user.username)
    """
    try:
        user_id = _resolve_id_from_arg(arg.data, USER_MENTION_REGEX)
    except ValueError:
        users = arg.context.bot.cache.get_users_view()
        user = utils.find(
            users.values(), lambda u: u.username == arg.data or f"{u.username}#{u.discriminator}" == arg.data
        )
    else:
        user = arg.context.bot.cache.get_user(user_id)
        if user is None:
            user = await arg.context.bot.rest.fetch_user(user_id)
    return _raise_if_not_none(user)


async def member_converter(arg: WrappedArg) -> hikari.Member:
    """
    Converter to transform a command argument into a :obj:`~hikari.Member` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.Member`: The member object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a member object.
    """
    try:
        user_id = _resolve_id_from_arg(arg.data, USER_MENTION_REGEX)
    except ValueError:
        members = arg.context.bot.cache.get_members_view_for_guild(arg.context.guild_id)
        member = utils.find(
            members.values(),
            lambda m: m.username == arg.data or m.nickname == arg.data or f"{m.username}#{m.discriminator}" == arg.data,
        )
    else:
        member = arg.context.bot.cache.get_member(arg.context.guild_id, user_id)
        if member is None:
            member = await arg.context.bot.rest.fetch_member(arg.context.guild_id, user_id)
    return _raise_if_not_none(member)


async def text_channel_converter(arg: WrappedArg) -> hikari.TextChannel:
    """
    Converter to transform a command argument into a :obj:`~hikari.GuildTextChannel` or
    :obj:`~hikari.channels.GuildNewsChannel` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`hikari.TextChannel`: The channel object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a channel object.
    """
    try:
        channel_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    except ValueError:
        channels = arg.context.bot.cache.get_guild_channels_view_for_guild(arg.context.guild_id)
        channel = utils.get(channels.values(), name=arg.data)
    else:
        channel = await _get_or_fetch_guild_channel_from_id(arg, channel_id)

    if not isinstance(channel, hikari.TextChannel):
        raise errors.ConverterFailure("Channel is not a text channel")
    return channel


async def guild_voice_channel_converter(arg: WrappedArg) -> hikari.GuildVoiceChannel:
    """
    Converter to transform a command argument into a :obj:`~hikari.GuildVoiceChannel` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.GuildVoiceChannel`: The channel object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a channel object.
    """
    try:
        channel_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    except ValueError:
        channels = arg.context.bot.cache.get_guild_channels_view_for_guild(arg.context.guild_id)
        channel = utils.get(channels.values(), name=arg.data)
    else:
        channel = await _get_or_fetch_guild_channel_from_id(arg, channel_id)

    if not isinstance(channel, hikari.GuildVoiceChannel):
        raise errors.ConverterFailure("Channel is not a guild voice channel")
    return channel


# Deprecated, as this may change in the future to not just be a GuildVoiceChannel should Discord add new features,
# so this shouldn't be used as it may cause breaking changes later.
def voice_channel_converter(arg: WrappedArg) -> typing.Coroutine[typing.Any, typing.Any, hikari.GuildVoiceChannel]:
    warnings.warn(
        "voice_channel_converter is deprecated, use guild_voice_channel_converter instead",
        category=DeprecationWarning,
    )
    return guild_voice_channel_converter(arg)


async def category_converter(arg: WrappedArg) -> hikari.GuildCategory:
    """
    Converter to transform a command argument into a :obj:`~hikari.GuildCategory` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.GuildCategory`: The category object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a category object.
    """
    try:
        channel_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    except ValueError:
        channels = arg.context.bot.cache.get_guild_channels_view_for_guild(arg.context.guild_id)
        channel = utils.get(channels.values(), name=arg.data)
    else:
        channel = await _get_or_fetch_guild_channel_from_id(arg, channel_id)

    if not isinstance(channel, hikari.GuildCategory):
        raise errors.ConverterFailure("Channel is not a guild category")
    return channel


async def role_converter(arg: WrappedArg) -> hikari.Role:
    """
    Converter to transform a command argument into a :obj:`~hikari.Role` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.Role`: The role object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a role object.
    """
    try:
        role_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    except ValueError:
        roles = arg.context.bot.cache.get_roles_view_for_guild(arg.context.guild_id)
        role = utils.get(roles.values(), name=arg.data)
    else:
        role = arg.context.bot.cache.get_role(role_id)
        if role is None:
            roles = await arg.context.bot.rest.fetch_roles(arg.context.guild_id)
            roles = dict([(r.id, r) for r in roles])
            role = roles[role_id]
    return _raise_if_not_none(role)


async def custom_emoji_converter(arg: WrappedArg) -> hikari.KnownCustomEmoji:
    """
    Converter to transform a command argument into a :obj:`~hikari.emojis.KnownCustomEmoji` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.emojis.KnownCustomEmoji`: The custom emoji object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a custom emoji object.
    """
    try:
        emoji_id = _resolve_id_from_arg(arg.data, EMOJI_MENTION_REGEX)
    except ValueError:
        emojis = arg.context.bot.cache.get_emojis_view_for_guild(arg.context.guild_id)
        emoji = utils.get(emojis.values(), name=arg.data)
    else:
        emoji = arg.context.bot.cache.get_emoji(emoji_id)
        if emoji is None:
            emoji = await arg.context.bot.rest.fetch_emoji(arg.context.guild_id, emoji_id)
    return _raise_if_not_none(emoji)


if typing.TYPE_CHECKING:
    user_converter = hikari.User
    member_converter = hikari.Member
    text_channel_converter = hikari.TextChannel
    guild_voice_channel_converter = hikari.GuildVoiceChannel
    voice_channel_converter = guild_voice_channel_converter
    category_converter = hikari.GuildCategory
    role_converter = hikari.Role
    custom_emoji_converter = hikari.KnownCustomEmoji
