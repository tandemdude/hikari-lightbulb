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
__all__ = [
    "Check",
    "owner_only",
    "guild_only",
    "dm_only",
    "bot_only",
    "webhook_only",
    "human_only",
    "nsfw_channel_only",
]

import functools
import typing as t

import hikari

from lightbulb_v2 import context as context_
from lightbulb_v2 import errors

T = t.TypeVar("T")
_CallbackT = t.Union[
    t.Callable[[context_.base.Context], t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]], functools.partial
]


class Check:
    """
    Class representing a check. Check functions can be syncronous or asyncronous functions which take
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
        add_hook: t.Optional[t.Callable[[T], T]] = None,
    ) -> None:
        self.prefix_callback = p_callback
        self.slash_callback = s_callback or p_callback
        self.message_callback = m_callback or p_callback
        self.user_callback = u_callback or p_callback
        self.add_to_object_hook = add_hook or (lambda o: o)

    def __repr__(self) -> str:
        return f"Check({self.__name__.strip('_')})"

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
    if isinstance(context, context_.prefix.PrefixContext):
        if context.author.is_bot or context.event.message.webhook_id is not None:
            raise errors.HumanOnly("This command can only be used by humans")
    if context.author.is_bot:
        raise errors.HumanOnly("This command can only be used by humans")
    return True


def _nsfw_channel_only(context: context_.base.Context) -> bool:
    if context.guild_id is None:
        raise errors.NSFWChannelOnly("This command can only be used in NSFW channels")
    channel = context.get_channel()
    if not isinstance(channel, hikari.GuildChannel) or not channel.is_nsfw:
        raise errors.NSFWChannelOnly("This command can only be used in NSFW channels")
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
"""Prevents a command from being used in any channel other than one marked as NSFW."""
