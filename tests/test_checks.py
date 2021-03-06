# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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
from hikari import messages
from hikari import Permissions
from hikari import Intents

from lightbulb import checks
from lightbulb import context
from lightbulb import commands
from lightbulb import Bot
from lightbulb import errors


@pytest.fixture()
def ctx():
    return mock.MagicMock(
        spec_set=context.Context(
            mock.MagicMock(spec_set=Bot),
            mock.MagicMock(spec_set=messages.Message),
            "",
            "",
            mock.MagicMock(spec_set=commands.Command),
        )
    )


@pytest.mark.asyncio
async def test_guild_only_passes(ctx):
    ctx.message.guild_id = 123456
    assert await checks._guild_only(ctx) is True


@pytest.mark.asyncio
async def test_guild_only_fails(ctx):
    ctx.message.guild_id = None
    with pytest.raises(errors.OnlyInGuild) as exc_info:
        await checks._guild_only(ctx)
    assert exc_info.type is errors.OnlyInGuild


@pytest.mark.asyncio
async def test_dm_only_passes(ctx):
    ctx.message.guild_id = None
    assert await checks._dm_only(ctx) is True


@pytest.mark.asyncio
async def test_dm_only_fails(ctx):
    ctx.message.guild_id = 123456
    with pytest.raises(errors.OnlyInDM) as exc_info:
        await checks._dm_only(ctx)
    assert exc_info.type is errors.OnlyInDM


@pytest.mark.asyncio
async def test_owner_only_passes(ctx):
    ctx.bot.owner_ids = [12345]
    ctx.message.author.id = 12345
    assert await checks._owner_only(ctx) is True


@pytest.mark.asyncio
async def test_owner_only_fails(ctx):
    ctx.bot.owner_ids = [12345]
    ctx.message.author.id = 54321
    with pytest.raises(errors.NotOwner) as exc_info:
        await checks._owner_only(ctx)
    assert exc_info.type is errors.NotOwner


@pytest.mark.asyncio
async def test_guild_owner_passes(ctx):
    ctx.author.id = 12345
    ctx.guild.owner_id = 12345
    ctx.bot.intents = Intents.GUILDS
    assert await checks._has_guild_permissions(ctx, permissions=[Permissions.ADMINISTRATOR])


def test_add_check_called_with_guild_only():
    deco = checks.guild_only()
    fake_command = deco(mock.Mock(spec_set=commands.Command))
    fake_command.add_check.assert_called_with(checks._guild_only)


def test_add_check_called_with_dm_only():
    deco = checks.dm_only()
    fake_command = deco(mock.Mock(spec_set=commands.Command))
    fake_command.add_check.assert_called_with(checks._dm_only)


def test_add_check_called_with_owner_only():
    deco = checks.owner_only()
    fake_command = deco(mock.Mock(spec_set=commands.Command))
    fake_command.add_check.assert_called_with(checks._owner_only)
