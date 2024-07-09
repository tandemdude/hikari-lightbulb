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
    "LocalizationFailedException",
    "ExecutionException",
    "HookFailedException",
    "ExecutionPipelineFailedException",
]

import typing as t

if t.TYPE_CHECKING:
    from lightbulb import context as context_
    from lightbulb.commands import execution


class LightbulbException(Exception):
    """Base class for all exceptions used by lightbulb."""


class LocalizationFailedException(LightbulbException):
    """
    Exception raised when a command or option is marked as being localized, but a value for the name or description
    could not be resolved.
    """


class ExecutionException(LightbulbException):
    """Base class for exceptions that can be encountered during a command execution pipeline."""


class HookFailedException(ExecutionException):
    """Exception raised when a command execution hook triggered a failure."""

    def __init__(self, cause: Exception, hook: execution.ExecutionHook) -> None:
        super().__init__(f"exception encountered during execution of hook {hook}")
        self.__cause__ = cause
        self.hook = hook
        """The hook that triggered the failure."""


class ExecutionPipelineFailedException(ExecutionException):
    """
    Exception raised when the execution of any step during command invocation failed. This is the
    exception type passed to all error handlers.

    If during execution, only a single exception was raised, the ``__cause__`` attribute will be
    set to that exception.
    """

    def __init__(
        self,
        hook_failures: t.Sequence[HookFailedException],
        invocation_failure: Exception | None,
        pipeline: execution.ExecutionPipeline,
        context: context_.Context,
    ) -> None:
        super().__init__(f"execution of command {context.command_data.qualified_name!r} failed")

        self.hook_failures = hook_failures
        """The exceptions caused by hook failures during command execution."""
        self.invocation_failure = invocation_failure
        """
        The exception caused by the invocation method failing during command execution. Will be :obj:`None` if
        the invocation method did not fail or was not executed.
        """
        self.pipeline = pipeline
        """The pipeline that failed."""
        self.context = context
        """The context that caused the pipeline to fail."""

        if len(causes := [*hook_failures, invocation_failure]) == 1:
            self.__cause__ = causes[0]
