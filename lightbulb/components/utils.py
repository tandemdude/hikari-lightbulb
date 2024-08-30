# -*- coding: utf-8 -*-
#
# api_ref_gen::ignore
#
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

__all__ = ["TaskLogSuppressorProxy"]

import typing as t

if t.TYPE_CHECKING:
    import asyncio
    from collections.abc import Generator

T = t.TypeVar("T")


class TaskLogSuppressorProxy(t.Generic[T]):
    """
    Slight bodge allowing suppression of error logging from tasks if they are awaited
    before the execution completes.
    """

    __slots__ = ("_task",)

    def __init__(self, task: asyncio.Task[T]) -> None:
        self._task = task

    def __await__(self) -> Generator[None, t.Any, T]:
        self._task.set_name(self._task.get_name() + "@suppress")
        return self._task.__await__()
