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
    "BaseConverter",
    "BooleanConverter",
    "ColorConverter",
    "ColourConverter",
    "EmojiConverter",
    "GuildCategoryConverter",
    "GuildChannelConverter",
    "GuildConverter",
    "GuildVoiceChannelConverter",
    "InviteConverter",
    "MemberConverter",
    "MessageConverter",
    "RoleConverter",
    "SnowflakeConverter",
    "TextableGuildChannelConverter",
    "TimestampConverter",
    "UserConverter",
]

import datetime
import typing as t

import hikari

from lightbulb.converters import base
from lightbulb.converters import special
from lightbulb.converters.base import *
from lightbulb.converters.special import *

CONVERTER_TYPE_MAPPING: t.Mapping[t.Any, t.Type[base.BaseConverter[t.Any]]] = {
    hikari.User: special.UserConverter,
    hikari.Member: special.MemberConverter,
    hikari.GuildChannel: special.GuildChannelConverter,
    hikari.TextableGuildChannel: special.TextableGuildChannelConverter,
    hikari.TextableChannel: special.TextableGuildChannelConverter,
    hikari.GuildCategory: special.GuildCategoryConverter,
    hikari.GuildVoiceChannel: special.GuildVoiceChannelConverter,
    hikari.Role: special.RoleConverter,
    hikari.Emoji: special.EmojiConverter,
    hikari.Guild: special.GuildConverter,
    hikari.Message: special.MessageConverter,
    hikari.Invite: special.InviteConverter,
    hikari.Colour: special.ColourConverter,
    hikari.Color: special.ColourConverter,
    hikari.Snowflake: special.SnowflakeConverter,
    datetime.datetime: special.TimestampConverter,
}
