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

import typing as t

if t.TYPE_CHECKING:
    from lightbulb.commands import execution


class LightbulbException(Exception):
    ...


class ExecutionException(LightbulbException):
    ...


class ExecutionHookFailedException(ExecutionException):
    def __init__(self, hook: execution.ExecutionHook, cause: Exception) -> None:
        super().__init__(f"exception encountered during execution of hook {hook}")
        self.hook = hook
        self.__cause__ = cause


class ExecutionFailedException(ExecutionException):
    def __init__(self, causes: t.Sequence[Exception], aborted: bool, step: execution.ExecutionStep) -> None:
        super().__init__(
            f"{'multiple exceptions ' if len(causes) > 1 else 'exception '}encountered during command execution"
        )

        if len(causes) == 1:
            self.__cause__ = causes[0]

        self.causes = causes
        self.aborted = aborted
        self.step = step

    @property
    def hook_exceptions(self) -> t.Sequence[ExecutionHookFailedException]:
        return [e for e in self.causes if isinstance(e, ExecutionHookFailedException)]

    @property
    def invocation_exception(self) -> t.Optional[Exception]:
        maybe_exc = [e for e in self.causes if not isinstance(e, ExecutionHookFailedException)]
        return maybe_exc[0] if maybe_exc else None
