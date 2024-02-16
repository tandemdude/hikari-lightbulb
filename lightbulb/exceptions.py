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

__all__ = [
    "LightbulbException",
    "ExecutionException",
    "HookFailedException",
    "InvocationFailedException",
    "PipelineFailedException",
]

import typing as t

if t.TYPE_CHECKING:
    from lightbulb import context as context_
    from lightbulb.commands import execution


class LightbulbException(Exception):
    """Base class for all exceptions used by lightbulb."""


class ExecutionException(LightbulbException):
    """Base class for exceptions that can be encountered during a command execution pipeline."""


class HookFailedException(ExecutionException):
    """Exception raised when a command execution hook triggered a failure."""

    def __init__(self, cause: Exception, hook: execution.ExecutionHook, abort: bool) -> None:
        super().__init__(f"exception encountered during execution of hook {hook}")
        self.__cause__ = cause
        self.hook = hook
        """The hook that triggered the failure."""
        self.abort = abort
        """Whether the failure caused the pipeline to be aborted."""


class InvocationFailedException(ExecutionException):
    """Exception raised when a command invocation function raised an error during execution."""

    def __init__(self, cause: Exception, context: context_.Context) -> None:
        super().__init__("exception encountered during command invocation")

        self.__cause__ = cause
        self.context = context
        """The context that caused the command invocation to fail."""


class PipelineFailedException(ExecutionException):
    """Exception raised when an :obj:`~lightbulb.commands.execution.ExecutionPipeline` run failed."""

    def __init__(self, causes: t.Sequence[Exception], pipeline: execution.ExecutionPipeline) -> None:
        super().__init__(
            f"{'multiple exceptions ' if len(causes) > 1 else 'exception '}encountered during command execution"
        )

        if len(causes) == 1:
            self.__cause__ = causes[0]

        self.causes = causes
        """The causes of the pipeline failure. If there is only one, the ``__cause__`` attribute will also be set."""
        self.pipeline = pipeline
        """The pipeline that failed - causing this exception to be thrown."""

    @property
    def step(self) -> t.Optional[execution.ExecutionStep]:
        """
        The execution step that the pipeline failed on. Will be :obj:`None` if all execution
        steps passed and the failure was instead caused by an exception raised by the command
        invocation function.

        Returns:
            :obj:`~typing.Optional` [ :obj:`~lightbulb.commands.execution.ExecutionStep` ]: The step that
                caused the failure, or :obj:`None` if caused by command invocation function.
        """
        return self.pipeline._current_step
