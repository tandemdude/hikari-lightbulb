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
"""
Module containing exceptions raised by lightbulb internals. Exceptions raised by built-in hooks (prefab package)
are instead kept within that package. See the ``lightbulb.prefab`` documentation page for their reference. Similarly,
exceptions raised by the dependency injection system are vendored by the ``lightbulb.di`` submodule.
"""

from __future__ import annotations

__all__ = [
    "ConversionFailedException",
    "ExecutionException",
    "ExecutionPipelineFailedException",
    "LightbulbException",
    "LocalizationFailedException",
]

import typing as t

D = t.TypeVar("D")
R = t.TypeVar("R")

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from lightbulb import context as context_
    from lightbulb.commands import execution
    from lightbulb.commands import options


class LightbulbException(Exception):
    """Base class for all exceptions used by lightbulb."""


class LocalizationFailedException(LightbulbException):
    """
    Exception raised when a command or option is marked as being localized, but a value for the name or description
    could not be resolved.
    """


class ConversionFailedException(LightbulbException):
    """Exception raised when a command option conversion fails."""

    def __init__(self, option: options.OptionData[D, R], value: t.Any) -> None:
        super().__init__(f"failed converting option {option._localized_name!r}")

        self.option: options.OptionData[t.Any, t.Any] = option
        """The data for the option that failed conversion."""
        self.value: t.Any = value
        """The value which could not be converted."""


class ExecutionException(LightbulbException):
    """Base class for exceptions that can be encountered during a command execution pipeline."""


class ExecutionPipelineFailedException(ExecutionException):
    """
    Exception raised when the execution of any step during command invocation failed. This is the
    exception type passed to all error handlers.

    If during execution, only a single exception was raised, the ``__cause__`` attribute will be
    set to that exception.
    """

    def __init__(
        self,
        failed_hooks_with_exceptions: Sequence[tuple[execution.ExecutionHook, Exception]],
        invocation_failure: Exception | None,
        pipeline: execution.ExecutionPipeline,
        context: context_.Context,
    ) -> None:
        super().__init__(f"execution of command {context.command_data.qualified_name!r} failed")

        self.failed_hooks: Sequence[execution.ExecutionHook] = [item[0] for item in failed_hooks_with_exceptions]
        """
        The hooks that failed during command execution.
        The corresponding exception can be found at the same index in ``hook_failures``.
        """
        self.hook_failures: Sequence[Exception] = [item[1] for item in failed_hooks_with_exceptions]
        """The exceptions caused by hook failures during command execution."""
        self.invocation_failure: Exception | None = invocation_failure
        """
        The exception caused by the invocation method failing during command execution. Will be :obj:`None` if
        the invocation method did not fail or was not executed.
        """
        self.pipeline: execution.ExecutionPipeline = pipeline
        """The pipeline that failed."""
        self.context: context_.Context = context
        """The context that caused the pipeline to fail."""

        self.causes: Sequence[Exception] = [e for e in [*self.hook_failures, invocation_failure] if e is not None]
        """All the exceptions raised during command execution."""

        if len(self.causes) == 1:
            self.__cause__: BaseException | None = self.causes[0]
