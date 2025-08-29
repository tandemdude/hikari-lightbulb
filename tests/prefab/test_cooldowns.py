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

import pytest

from lightbulb.prefab import cooldowns

mock_context = mock.Mock()
mock_context.client = mock.Mock(_features={})


class TestBuckets:
    def test_global_bucket_returns_same_hash_every_time(self) -> None:
        bucket = cooldowns._PROVIDED_BUCKETS["global"]
        assert bucket(mock.Mock()) == bucket(mock.Mock())

    def test_user_bucket_returns_correct_value(self) -> None:
        context = mock.Mock(user=mock.Mock(id=12345))
        assert cooldowns._PROVIDED_BUCKETS["user"](context) == 12345

    def test_channel_bucket_returns_correct_value(self) -> None:
        context = mock.Mock(channel_id=12345)
        assert cooldowns._PROVIDED_BUCKETS["channel"](context) == 12345

    def test_guild_bucket_returns_correct_value_in_guild(self) -> None:
        context = mock.Mock(guild_id=12345)
        assert cooldowns._PROVIDED_BUCKETS["guild"](context) == 12345

    def test_guild_bucket_returns_correct_value_in_dm(self) -> None:
        context = mock.Mock(guild_id=None, channel_id=12345)
        assert cooldowns._PROVIDED_BUCKETS["guild"](context) == 12345


class TestFixedWindow:
    @pytest.mark.asyncio
    async def test_accepts_first_invocation(self) -> None:
        hook = cooldowns.fixed_window(10, 5, "global")
        await hook(mock.Mock(), mock_context)

    @pytest.mark.asyncio
    async def test_blocks_too_many_invocations_within_window(self) -> None:
        hook = cooldowns.fixed_window(10, 1, "global")
        await hook(mock.Mock(), mock_context)

        with pytest.raises(cooldowns.OnCooldown):
            await hook(mock.Mock(), mock_context)

    @pytest.mark.asyncio
    async def test_allows_invocation_once_window_expires(self) -> None:
        hook = cooldowns.fixed_window(1, 1, "global")

        with mock.patch("time.perf_counter", side_effect=[0, 0.5, 1.1]):
            await hook(mock.Mock(), mock_context)
            with pytest.raises(cooldowns.OnCooldown):
                await hook(mock.Mock(), mock_context)

            await hook(mock.Mock(), mock_context)


class TestSlidingWindow:
    @pytest.mark.asyncio
    async def test_accepts_first_invocation(self) -> None:
        hook = cooldowns.sliding_window(10, 5, "global")
        await hook(mock.Mock(), mock_context)

    @pytest.mark.asyncio
    async def test_blocks_too_many_invocations_within_window(self) -> None:
        hook = cooldowns.sliding_window(10, 1, "global")
        await hook(mock.Mock(), mock_context)

        with pytest.raises(cooldowns.OnCooldown):
            await hook(mock.Mock(), mock_context)

    @pytest.mark.asyncio
    async def test_allows_invocation_once_previous_drops_out_of_window(self) -> None:
        hook = cooldowns.sliding_window(5, 2, "global")

        with mock.patch("time.perf_counter", side_effect=[0, 2.5, 6, 6.5]):
            await hook(mock.Mock(), mock_context)
            await hook(mock.Mock(), mock_context)
            await hook(mock.Mock(), mock_context)

            with pytest.raises(cooldowns.OnCooldown):
                await hook(mock.Mock(), mock_context)
