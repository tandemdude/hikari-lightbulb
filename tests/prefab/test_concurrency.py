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

from lightbulb.prefab import concurrency

mock_context = mock.Mock()
mock_context.client = mock.Mock(_features={})


class TestMaxConcurrency:
    @pytest.mark.asyncio
    async def test_allows_invocations_under_limit(self) -> None:
        incr, _ = concurrency.max_concurrency(2, "global")
        await incr(mock.Mock(), mock_context)

    @pytest.mark.asyncio
    async def test_blocks_invocations_over_limit(self) -> None:
        incr, _ = concurrency.max_concurrency(1, "global")
        await incr(mock.Mock(), mock_context)

        with pytest.raises(concurrency.MaxConcurrencyReached):
            await incr(mock.Mock(), mock_context)

    @pytest.mark.asyncio
    async def test_allows_invocation_after_complete(self) -> None:
        incr, decr = concurrency.max_concurrency(1, "global")
        await incr(mock.Mock(), mock_context)

        with pytest.raises(concurrency.MaxConcurrencyReached):
            await incr(mock.Mock(), mock_context)
        await decr(mock.Mock(), mock_context)

        await incr(mock.Mock(), mock_context)
