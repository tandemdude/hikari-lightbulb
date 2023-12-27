# -*- coding: utf-8 -*-
# Copyright © tandemdude 2023-present
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
import datetime

import hikari


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
