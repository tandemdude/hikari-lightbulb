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
import asyncio
from unittest import mock

import pytest

from lightbulb.components import menus


def make_context(timeout: asyncio.Timeout | None) -> menus.MenuContext:
    return menus.MenuContext(
        mock.Mock(), mock.Mock(), mock.Mock(), mock.Mock(), timeout, asyncio.Event(), asyncio.Event()
    )


class TestMenuContextTimeout:
    @pytest.mark.asyncio
    async def test_extend_timeout_moves_deadline_forward(self) -> None:
        async with asyncio.timeout(10) as tm:  # noqa: ASYNC100
            deadline = tm.when()
            assert deadline is not None

            make_context(tm).extend_timeout(5)
            assert tm.when() == deadline + 5

    @pytest.mark.asyncio
    async def test_set_timeout_sets_deadline_relative_to_now(self) -> None:
        loop = asyncio.get_running_loop()
        async with asyncio.timeout(10) as tm:  # noqa: ASYNC100
            before = loop.time()
            make_context(tm).set_timeout(60)
            after = loop.time()

            deadline = tm.when()
            assert deadline is not None
            assert before + 60 <= deadline <= after + 60

    @pytest.mark.asyncio
    async def test_extended_timeout_does_not_expire_early(self) -> None:
        async with asyncio.timeout(0.05) as tm:
            make_context(tm).extend_timeout(0.1)
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_timeout_methods_do_nothing_without_timeout(self) -> None:
        ctx = make_context(None)
        ctx.extend_timeout(5)
        ctx.set_timeout(5)
