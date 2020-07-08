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
import mock
import pytest
import datetime

from hikari.models import messages, guilds
from lightbulb import Bot
from lightbulb import context
from lightbulb import commands


@pytest.fixture()
def message():
    return mock.MagicMock(spec_set=messages.Message)


@pytest.fixture()
def bot():
    return mock.MagicMock(spec_set=Bot)


@pytest.fixture()
def command():
    return mock.MagicMock(spec_set=commands.Command)


@pytest.mark.asyncio
async def test_context_guild_id_property(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    ctx.message.guild_id = 123456
    assert ctx.guild_id == 123456


@pytest.mark.asyncio
async def test_context_channel_id_property(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    ctx.message.channel_id = 123456
    assert ctx.channel_id == 123456


@pytest.mark.asyncio
async def test_context_content_property(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    ctx.message.content = "super cool message"
    assert ctx.content == "super cool message"


@pytest.mark.asyncio
async def test_context_member_property(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    mem = mock.MagicMock(spec_set=guilds.Member)
    ctx.message.member = mem
    assert ctx.member is mem


@pytest.mark.asyncio
async def test_context_message_id_property(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    ctx.message.id = 123456
    assert ctx.message_id == 123456


@pytest.mark.asyncio
async def test_context_timestamp_property(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    dt = datetime.datetime.now()
    ctx.message.timestamp = dt
    assert ctx.timestamp is dt


@pytest.mark.asyncio
async def test_context_edited_timestamp_property(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    dt = datetime.datetime.now()
    ctx.message.edited_timestamp = dt
    assert ctx.edited_timestamp is dt


@pytest.mark.asyncio
async def test_context_reply(bot, message, command):
    ctx = context.Context(bot, message, "", "", command)
    msg = "super cool message"
    await ctx.reply(msg)
    message.reply.assert_called_with(msg)
