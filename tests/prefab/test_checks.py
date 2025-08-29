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
from unittest import mock

import hikari
import pytest

import lightbulb


class TestOwnerOnly:
    @pytest.fixture(scope="function")
    def application(self) -> hikari.Application:
        app = mock.Mock(spec=hikari.Application)
        app.owner.id = 123
        app.team.members = {
            456: mock.Mock(),
            789: mock.Mock(),
        }

        return app

    @pytest.mark.asyncio
    async def test_raises_not_owner_when_user_is_not_owner(self) -> None:
        client: lightbulb.Client = mock.Mock(_owner_ids={123, 456, 789}, _features={})

        ctx = mock.Mock(spec=lightbulb.Context, client=client)
        ctx.user.id = 000

        with pytest.raises(lightbulb.prefab.NotOwner):
            await lightbulb.prefab.owner_only(mock.Mock(), ctx)

    @pytest.mark.asyncio
    async def test_does_not_raise_not_owner_when_user_is_owner(self) -> None:
        client: lightbulb.Client = mock.Mock(_owner_ids={123, 456, 789}, _features={})

        ctx = mock.Mock(spec=lightbulb.Context, client=client)
        ctx.user.id = 123

        await lightbulb.prefab.owner_only(mock.Mock(), ctx)

    @pytest.mark.asyncio
    async def test_gets_correct_owner_ids_from_application(self, application: hikari.Application) -> None:
        client: lightbulb.Client = mock.Mock(_owner_ids=None, _features={})
        client._ensure_application = mock.AsyncMock(return_value=application)

        ctx = mock.Mock(spec=lightbulb.Context, client=client)
        ctx.user.id = 123

        await lightbulb.prefab.owner_only(mock.Mock(), ctx)
        assert client._owner_ids == {123, 456, 789}


class TestHasPermissions:
    @pytest.fixture(scope="function")
    def context(self) -> lightbulb.Context:
        ctx = mock.Mock(spec=lightbulb.Context)
        ctx.client = mock.Mock(_features={})
        ctx.member = mock.Mock(permissions=hikari.Permissions.all_permissions())
        return ctx

    @pytest.mark.asyncio
    async def test_passes_when_user_has_permissions(self, context: lightbulb.Context) -> None:
        await lightbulb.prefab.has_permissions(hikari.Permissions.SEND_MESSAGES)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_fails_when_user_does_not_have_permissions(self, context: lightbulb.Context) -> None:
        context.member.permissions = hikari.Permissions.ADD_REACTIONS  # type: ignore[reportOptionalMemberAccess]

        with pytest.raises(lightbulb.prefab.MissingRequiredPermission) as exc_info:
            await lightbulb.prefab.has_permissions(hikari.Permissions.SEND_MESSAGES)(mock.Mock(), context)

            assert exc_info.value.missing == hikari.Permissions.SEND_MESSAGES
            assert exc_info.value.actual == hikari.Permissions.ADD_REACTIONS

    @pytest.mark.asyncio
    async def test_fails_when_not_in_guild(self, context: lightbulb.Context) -> None:
        context.member = None  # type: ignore[reportAttributeAccessIssue]

        with pytest.raises(lightbulb.prefab.MissingRequiredPermission):
            await lightbulb.prefab.has_permissions(hikari.Permissions.ADMINISTRATOR)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_passes_when_not_in_guild_fail_flag_disabled(self, context: lightbulb.Context) -> None:
        context.member = None  # type: ignore[reportAttributeAccessIssue]
        await lightbulb.prefab.has_permissions(hikari.Permissions.ADMINISTRATOR, fail_in_dm=False)(mock.Mock(), context)


class TestBotHasPermissions:
    @pytest.fixture(scope="function")
    def context(self) -> lightbulb.Context:
        ctx = mock.Mock(spec=lightbulb.Context)
        ctx.client = mock.Mock(_features={})
        ctx.interaction = mock.Mock(app_permissions=hikari.Permissions.all_permissions())
        return ctx

    @pytest.mark.asyncio
    async def test_passes_when_user_has_permissions(self, context: lightbulb.Context) -> None:
        await lightbulb.prefab.bot_has_permissions(hikari.Permissions.SEND_MESSAGES)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_fails_when_user_does_not_have_permissions(self, context: lightbulb.Context) -> None:
        context.interaction.app_permissions = hikari.Permissions.ADD_REACTIONS

        with pytest.raises(lightbulb.prefab.BotMissingRequiredPermissions) as exc_info:
            await lightbulb.prefab.bot_has_permissions(hikari.Permissions.SEND_MESSAGES)(mock.Mock(), context)

            assert exc_info.value.missing == hikari.Permissions.SEND_MESSAGES
            assert exc_info.value.actual == hikari.Permissions.ADD_REACTIONS

    @pytest.mark.asyncio
    async def test_fails_when_not_in_guild(self, context: lightbulb.Context) -> None:
        context.guild_id = None  # type: ignore[reportAttributeAccess]

        with pytest.raises(lightbulb.prefab.BotMissingRequiredPermissions):
            await lightbulb.prefab.bot_has_permissions(hikari.Permissions.ADMINISTRATOR)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_passes_when_not_in_guild_fail_flag_disabled(self, context: lightbulb.Context) -> None:
        context.guild_id = None  # type: ignore[reportAttributeAccess]
        await lightbulb.prefab.bot_has_permissions(hikari.Permissions.ADMINISTRATOR, fail_in_dm=False)(
            mock.Mock(), context
        )


class TestHasRoles:
    @pytest.fixture(scope="function")
    def context(self) -> lightbulb.Context:
        ctx = mock.Mock(spec=lightbulb.Context)
        ctx.client = mock.Mock(_features={})
        ctx.member = mock.Mock(role_ids=[123, 456, 789])
        return ctx

    @pytest.mark.asyncio
    async def test_passes_when_user_has_all_roles(self, context: lightbulb.Context) -> None:
        await lightbulb.prefab.has_roles(123, 456, 789)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_passes_when_user_has_any_role(self, context: lightbulb.Context) -> None:
        context.member.role_ids = [123, 987, 654]  # type: ignore[reportOptionalMemberAccess]
        await lightbulb.prefab.has_roles(123, 456, 789, mode="any")(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_fails_when_user_has_no_roles_all_mode(self, context: lightbulb.Context) -> None:
        context.member.role_ids = []  # type: ignore[reportOptionalMemberAccess]
        with pytest.raises(lightbulb.prefab.MissingRequiredRoles):
            await lightbulb.prefab.has_roles(123, 456, 789)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_fails_when_user_has_some_roles_all_mode(self, context: lightbulb.Context) -> None:
        context.member.role_ids = [123, 456]  # type: ignore[reportOptionalMemberAccess]
        with pytest.raises(lightbulb.prefab.MissingRequiredRoles) as exc_info:
            await lightbulb.prefab.has_roles(123, 456, 789)(mock.Mock(), context)

            assert exc_info.value.role_ids == [789]

    @pytest.mark.asyncio
    async def test_fails_when_user_has_no_roles_any_mode(self, context: lightbulb.Context) -> None:
        context.member.role_ids = []  # type: ignore[reportOptionalMemberAccess]
        with pytest.raises(lightbulb.prefab.MissingRequiredRoles) as exc_info:
            await lightbulb.prefab.has_roles(123, 456, 789, mode="any")(mock.Mock(), context)

            assert exc_info.value.role_ids == [123, 456, 789]

    @pytest.mark.asyncio
    async def test_fails_when_in_dm_and_fail_in_dm_true(self, context: lightbulb.Context) -> None:
        context.member = None  # type: ignore[reportAttributeAccessIssue]

        with pytest.raises(lightbulb.prefab.MissingRequiredRoles):
            await lightbulb.prefab.has_roles(123, 456, 789)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_passes_when_in_dm_and_fail_in_dm_false(self, context: lightbulb.Context) -> None:
        context.member = None  # type: ignore[reportAttributeAccessIssue]
        await lightbulb.prefab.has_roles(123, 456, 789, fail_in_dm=False)(mock.Mock(), context)

    @pytest.mark.asyncio
    async def test_passes_when_role_ids_passed_in_as_iterable(self, context: lightbulb.Context) -> None:
        await lightbulb.prefab.has_roles([123, 456, 789])(mock.Mock(), context)
