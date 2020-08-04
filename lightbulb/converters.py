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
    "voice_channel_converter",
    "category_converter",
    "role_converter",
]

import re
import typing
import collections

import hikari

from lightbulb import context
from lightbulb import errors

USER_MENTION_REGEX: typing.Final[typing.Pattern] = re.compile(r"<@!?(\d+)>")
CHANNEL_MENTION_REGEX: typing.Final[typing.Pattern] = re.compile(r"<#(\d+)>")
ROLE_MENTION_REGEX: typing.Final[typing.Pattern] = re.compile(r"<@&(\d+)>")


class WrappedArg(collections.UserString):
    """
    A wrapped command argument containing the invocation context
    of the command for which the argument is to be converted under.

    This class acts like a string so any operations that will work on a string will
    also work on this class.

    The raw string argument can be accessed through the :attr:`data` attribute.

    Args:
        seq (:obj:`str`): The argument text.
        context (:obj:`~.context.Context`): The command invocation context for the argument.
    """

    def __init__(self, seq: str, context: context.Context) -> None:
        super().__init__(seq)
        self.context = context


def _resolve_id_from_arg(arg_string: str, regex: typing.Pattern) -> hikari.Snowflake:
    if match := regex.match(arg_string):
        arg_string = match.group(1)
    return hikari.Snowflake(arg_string)


async def _get_or_fetch_guild_channel_from_id(arg: WrappedArg, channel_id: hikari.Snowflake) -> hikari.GuildChannel:
    channel = None
    if arg.context.bot._has_stateful_cache:
        channel = arg.context.bot.cache.get_guild_channel(channel_id)
    if channel is None:
        channel = await arg.context.bot.rest.fetch_channel(channel_id)
    return channel


async def user_converter(arg: WrappedArg) -> hikari.User:
    """
    Converter to transform a command argument into a :obj:`hikari.models.users.UserImpl` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`hikari.models.users.UserImpl`: The user object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a user object.

    Example:

        .. code-block:: python

            @bot.command()
            async def username(ctx, user: lightbulb.converters.user_converter):
                await ctx.reply(user.username)
    """
    user_id = _resolve_id_from_arg(arg.data, USER_MENTION_REGEX)
    if arg.context.bot._has_stateful_cache:
        if (user := arg.context.bot.cache.get_user(user_id)) is not None:
            return user
    return await arg.context.bot.rest.fetch_user(user_id)


async def member_converter(arg: WrappedArg) -> hikari.Member:
    """
    Converter to transform a command argument into a :obj:`~hikari.models.guilds.Member` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.models.guilds.Member`: The member object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a member object.
    """
    # TODO - Implement cache checking
    user_id = _resolve_id_from_arg(arg.data, USER_MENTION_REGEX)
    if arg.context.bot._has_stateful_cache:
        if (member := arg.context.bot.cache.get_member(arg.context.guild_id, user_id)) is not None:
            return member
    return await arg.context.bot.rest.fetch_member(arg.context.guild_id, user_id)


async def text_channel_converter(arg: WrappedArg) -> typing.Union[hikari.GuildTextChannel, hikari.GuildNewsChannel]:
    """
    Converter to transform a command argument into a :obj:`~hikari.models.channels.GuildTextChannel` or
    :obj:`~hikari.models.channels.GuildNewsChannel` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        Union[ :obj:`~hikari.models.channels.GuildTextChannel`, :obj:`~hikari.models.channels.GuildNewsChannel`]: The
        channel object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a channel object.
    """
    # TODO - Implement cache checking
    channel_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    channel = await _get_or_fetch_guild_channel_from_id(arg, channel_id)
    if not isinstance(channel, (hikari.GuildTextChannel, hikari.GuildNewsChannel)):
        raise errors.ConverterFailure("Channel is not a text channel")
    return channel


async def voice_channel_converter(arg: WrappedArg) -> hikari.GuildVoiceChannel:
    """
    Converter to transform a command argument into a :obj:`~hikari.models.channels.GuildVoiceChannel` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.models.channels.GuildVoiceChannel`: The channel object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a channel object.
    """
    # TODO - Implement cache checking
    channel_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    channel = await _get_or_fetch_guild_channel_from_id(arg, channel_id)
    if not isinstance(channel, hikari.GuildVoiceChannel):
        raise errors.ConverterFailure("Channel is not a voice channel")
    return channel


async def category_converter(arg: WrappedArg) -> hikari.GuildCategory:
    """
    Converter to transform a command argument into a :obj:`~hikari.models.channels.GuildCategory` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.models.channels.GuildCategory`: The category object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a category object.
    """
    # TODO - Implement cache checking
    channel_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    channel = await _get_or_fetch_guild_channel_from_id(arg, channel_id)
    if not isinstance(channel, hikari.GuildCategory):
        raise errors.ConverterFailure("Channel is not a voice channel")
    return channel


async def role_converter(arg: WrappedArg) -> hikari.Role:
    """
    Converter to transform a command argument into a :obj:`~hikari.models.guilds.Role` object.

    Args:
        arg (:obj:`WrappedArg`): Argument to transform.

    Returns:
        :obj:`~hikari.models.guilds.Role`: The role object resolved from the argument.

    Raises:
        :obj:`~.errors.ConverterFailure`: If the argument could not be resolved into a role object.
    """
    # TODO - Implement cache checking
    role_id = _resolve_id_from_arg(arg.data, CHANNEL_MENTION_REGEX)
    if arg.context.bot._has_stateful_cache:
        if (role := arg.context.bot.cache.get_role(role_id)) is not None:
            return role
    roles = await arg.context.bot.rest.fetch_roles(arg.context.guild_id)
    roles = dict([(r.id, r) for r in roles])
    return roles[role_id]
