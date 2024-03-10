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
from __future__ import annotations

__all__ = ["EMPTY_USER", "EMPTY_MESSAGE", "EMPTY_CHANNEL", "EMPTY_ROLE", "get_command_data"]

import datetime
import typing as t

import hikari

if t.TYPE_CHECKING:
    from lightbulb.commands import commands


class _EmptyUser(hikari.User):
    __slots__ = ()

    app = property(lambda self: None)
    id = property(lambda self: hikari.Snowflake(0))
    accent_color = property(lambda self: None)
    avatar_hash = property(lambda self: None)
    banner_hash = property(lambda self: None)
    discriminator = property(lambda self: "")
    flags = property(lambda self: hikari.UserFlag.NONE)
    is_bot = property(lambda self: False)
    is_system = property(lambda self: False)
    mention = property(lambda self: "")
    username = property(lambda self: "")
    global_name = property(lambda self: "")


EMPTY_USER = _EmptyUser()
"""Placeholder for a user. Used when attempting to get value for an option on a class instead of instance."""
EMPTY_MESSAGE = hikari.Message(
    app=None,  # type: ignore[reportGeneralTypeIssues]
    id=hikari.Snowflake(0),
    channel_id=hikari.Snowflake(0),
    guild_id=None,
    author=EMPTY_USER,
    member=None,
    content=None,
    timestamp=datetime.datetime.fromtimestamp(0, datetime.timezone.utc),
    edited_timestamp=None,
    is_tts=False,
    attachments=(),
    embeds=(),
    reactions=(),
    is_pinned=False,
    webhook_id=hikari.Snowflake(0),
    type=hikari.MessageType.DEFAULT,
    activity=None,
    application=None,
    message_reference=None,
    referenced_message=None,
    flags=hikari.MessageFlag.NONE,
    stickers=(),
    nonce=None,
    application_id=hikari.Snowflake(0),
    interaction=None,
    components=(),
    user_mentions=hikari.UNDEFINED,
    channel_mentions=hikari.UNDEFINED,
    role_mention_ids=hikari.UNDEFINED,
    mentions_everyone=hikari.UNDEFINED,
)
"""Placeholder for a message. Used when attempting to get value for an option on a class instead of instance."""
EMPTY_CHANNEL = hikari.PartialChannel(
    app=None,  # type: ignore[reportGeneralTypeIssues]
    id=hikari.Snowflake(0),
    name="",
    type=hikari.ChannelType.GUILD_TEXT,
)
EMPTY_ROLE = hikari.Role(
    app=None,  # type: ignore[reportGeneralTypeIssues]
    id=hikari.Snowflake(0),
    name="",
    color=hikari.Color.from_int(0),
    guild_id=hikari.Snowflake(0),
    is_hoisted=False,
    icon_hash=None,
    unicode_emoji=None,
    is_managed=False,
    is_mentionable=False,
    permissions=hikari.Permissions.NONE,
    position=0,
    bot_id=None,
    integration_id=None,
    is_premium_subscriber_role=False,
    subscription_listing_id=None,
    is_available_for_purchase=False,
    is_guild_linked_role=False,
)
"""Placeholder for a role. Used when attempting to get value for an option on a class instead of instance."""
EMPTY_ATTACHMENT = hikari.Attachment(
    id=hikari.Snowflake(0),
    url="",
    filename="",
    media_type=None,
    size=0,
    proxy_url="",
    height=None,
    width=None,
    is_ephemeral=False,
    duration=None,
    waveform=None,
)
"""Placeholder for an attachment. Used when attempting to get value for an option on a class instead of instance."""


def get_command_data(command: commands.CommandBase | type[commands.CommandBase]) -> commands.CommandData:
    """
    Utility method to get the command data dataclass for a command instance or command class.

    Args:
        command (:obj:`~typing.Union` [ :obj:`~lightbulb.commands.commands.CommandBase`, :obj:`~typing.Type` [ :obj:`~lightbulb.commands.commands.CommandBase` ]]): The
            command instance or command class to get the command data for.

    Returns:
        :obj:`~lightbulb.commands.commands.CommandData`: Command data dataclass for the given command.
    """  # noqa: E501
    return command._command_data
