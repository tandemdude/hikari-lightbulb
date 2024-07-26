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

import collections
import dataclasses
import typing as t

from lightbulb import di
from lightbulb import exceptions
from lightbulb import utils
from lightbulb.internal import constants
from lightbulb.internal import types

if t.TYPE_CHECKING:
    from lightbulb import context as context_

__all__ = ["ExecutionStep", "ExecutionSteps", "ExecutionHook", "ExecutionPipeline", "hook", "invoke"]

ExecutionHookFunc: t.TypeAlias = t.Callable[
    't.Concatenate["ExecutionPipeline", "context_.Context", ...]', types.MaybeAwaitable[None]
]


@dataclasses.dataclass(frozen=True, slots=True, eq=True)
class ExecutionStep:
    """
    Dataclass representing an execution step processed prior to the command invocation
    function being called.

    Args:
        name: The name of the execution step.
    """

    name: str
    """The name of the execution step"""

    __all_steps: t.ClassVar[t.Set[str]] = set()

    def __post_init__(self) -> None:
        if self.name in ExecutionStep.__all_steps:
            raise RuntimeError(f"a step with name {self.name} already exists")
        ExecutionStep.__all_steps.add(self.name)


@t.final
class ExecutionSteps:
    """Collection of the default execution steps lightbulb implements."""

    __slots__ = ()

    MAX_CONCURRENCY = ExecutionStep("MAX_CONCURRENCY")
    """Step for execution of maximum command concurrency logic."""
    CHECKS = ExecutionStep("CHECKS")
    """Step for execution of command check logic."""
    COOLDOWNS = ExecutionStep("COOLDOWNS")
    """Step for execution of command cooldown logic."""
    PRE_INVOKE = ExecutionStep("PRE_INVOKE")
    """Step for pre-invocation logic."""
    INVOKE = ExecutionStep("INVOKE")
    """Step for command invocation. No hooks should ever use this step."""
    POST_INVOKE = ExecutionStep("POST_INVOKE")
    """Step for post-invocation logic."""


@dataclasses.dataclass(frozen=True, slots=True, eq=True)
class ExecutionHook:
    """
    Dataclass representing a command execution hook executed before the invocation method is called.

    Args:
        step: The step that this hook should be run during.
        skip_when_failed: Whether this hook should be skipped if the pipeline has already failed.
        func: The function that this hook executes. May either be synchronous or asynchronous, and **must** take
            (at least) two arguments - and instance of :obj:`~ExecutionPipeline` and :obj:`~lightbulb.context.Context`
            respectively.
    """

    step: ExecutionStep
    """The step that this hook should be run during."""
    skip_when_failed: bool
    """Whether this hook should be skipped if the pipeline has already failed."""
    func: ExecutionHookFunc
    """The function that this hook executes."""

    async def __call__(self, pipeline: ExecutionPipeline, context: context_.Context) -> None:
        await utils.maybe_await(self.func(pipeline, context))


class ExecutionPipeline:
    """
    Class representing an entire command execution flow. Handles processing command hooks, including
    failure handling and collecting, as well as the calling of the command invocation function if
    all hooks succeed.

    Warning:
        A single hook failure **will not** prevent future hooks from being executed. If a hook should not
        be executed if previous ones have failed you can set the `skip_when_failed` parameter to prevent this from
        happening.

        .. code-block:: python

            @lightbulb.hook(lightbulb.ExecutionSteps.CHECKS, skip_when_failed=True)
            async def some_hook(pl: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
                ...

        Alternatively if you wish to customize the behaviour further you can add a guard clause in the hook
        function.

        .. code-block:: python

            @lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
            async def some_hook(pl: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
                # Prevent the hook from running if previous hooks (or the command invocation) failed.
                # Also see 'ExecutionPipeline.any_hook_failed' and 'ExecutionPipeline.invocation_failed' for
                # alternative behaviour.
                if pl.failed:
                    return

                ...
    """

    __slots__ = (
        "_context",
        "_remaining",
        "_hooks",
        "_current_step",
        "_current_hook",
        "_hook_failures",
        "_invocation_failure",
    )

    def __init__(self, context: context_.Context, order: t.Sequence[ExecutionStep]) -> None:
        self._context = context
        self._remaining = list(order)

        self._hooks: dict[ExecutionStep, list[ExecutionHook]] = collections.defaultdict(list)
        for hook in [*context.client.hooks, *context.command_data.hooks]:
            self._hooks[hook.step].append(hook)

        self._current_step: ExecutionStep | None = None
        self._current_hook: ExecutionHook | None = None

        self._hook_failures: list[tuple[ExecutionHook, Exception]] = []
        self._invocation_failure: Exception | None = None

    @property
    def failed(self) -> bool:
        """
        Whether this pipeline has failed.

        A pipeline is considered failed if any single hook execution failed, or the command invocation failed.

        Note:
            This **will** be :obj:`True` even if the failed hook(s) were executed **after** the command
            invocation function. Use :obj:`~ExecutionPipeline.invocation_failed` if you need to know if the
            invocation function threw an exception.
        """
        return self.any_hook_failed or self.invocation_failed

    @property
    def any_hook_failed(self) -> bool:
        """
        Whether any single invocation hook threw an exception.

        Note:
            This **will** be :obj:`True` even if the failed hook(s) were executed **after** the command
            invocation function. Use :obj:`~ExecutionPipeline.invocation_failed` if you need to know if the
            invocation function threw an exception.
        """
        return len(self._hook_failures) > 0

    @property
    def invocation_failed(self) -> bool:
        """Whether the command invocation function threw an exception."""
        return self._invocation_failure is not None

    def _next_step(self) -> ExecutionStep | None:
        """
        Return the next execution step to run, or :obj:`None` if the remaining execution steps
        have been exhausted.

        Returns:
            :obj:`~ExecutionStep` | :obj:`None`: The new execution step, or :obj:`None` if there
                are none remaining
        """
        if self._remaining:
            return self._remaining.pop(0)
        return None

    def _fail(self, exc: Exception) -> None:
        assert self._current_step is not None
        assert self._current_hook is not None

        self._hook_failures.append((self._current_hook, exc))

    async def _run(self) -> None:
        """
        Run the pipeline. Does not reset the state if called multiple times.
        To run the command again a new pipeline should be created.

        Returns:
            :obj:`None`

        Raises:
            :obj:`~lightbulb.exceptions.ExecutionPipelineFailedException`: If any hook or the command invocation
                raised an error
        """
        self._current_step = self._next_step()
        while self._current_step is not None:
            if self._current_step == ExecutionSteps.INVOKE and not self.failed:
                try:
                    await getattr(self._context.command, self._context.command_data.invoke_method)(self._context)
                    self._current_step = self._next_step()
                except Exception as e:
                    self._invocation_failure = e

                continue

            step_hooks = list(self._hooks.get(self._current_step, []))
            while step_hooks:
                self._current_hook = step_hooks.pop(0)

                if self.failed and self._current_hook.skip_when_failed:
                    continue

                try:
                    await self._current_hook(self, self._context)
                except Exception as e:
                    self._fail(e)

            self._current_step = self._next_step()

        if self.failed:
            raise exceptions.ExecutionPipelineFailedException(
                self._hook_failures,
                self._invocation_failure,
                self,
                self._context,
            )


def hook(step: ExecutionStep, skip_when_failed: bool = False) -> t.Callable[[ExecutionHookFunc], ExecutionHook]:
    """
    Second order decorator to convert a function into an execution hook for the given
    step. Also enables dependency injection on the decorated function.

    The decorated function can be either synchronous or asyncronous and **must** take at minimum the
    two arguments seen below. ``pl`` is an instance of :obj:`~ExecutionPipeline` which is used to manage
    the command execution flow, and ``ctx`` is an instance of :obj:`~lightbulb.context.Context` which contains
    information about the current invocation.

    .. code-block:: python

        def example_hook(pl: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
            # Hook logic
            ...

    Args:
        step: The step that this hook should be run during.
        skip_when_failed: Whether this hook should be skipped if the :obj:`~ExecutionPipeline`
            has already failed due to a different hook or command invocation exception. Defaults to :obj:`False`.

    Returns:
        :obj:`~ExecutionHook`: The created execution hook.

    Example:
        To implement a custom hook to block execution of a command on days other than monday.

        .. code-block:: python

            @lightbulb.hook(lightbulb.ExecutionStep.CHECKS)
            def only_on_mondays(pl: lightbulb.ExecutionPipeline, _: lightbulb.Context) -> None:
                # Check if today is Monday (0)
                if datetime.date.today().weekday() != 0:
                    # Fail the pipeline execution
                    raise RuntimeError("This command can only be used on mondays!")
    """
    if step == ExecutionSteps.INVOKE:
        raise ValueError("hooks cannot be registered for the 'INVOKE' execution step")

    def inner(func: ExecutionHookFunc) -> ExecutionHook:
        return ExecutionHook(step, skip_when_failed, di.with_di(func))

    return inner


def invoke(
    func: t.Callable[..., t.Awaitable[t.Any]],
) -> t.Callable[[context_.Context], t.Awaitable[t.Any]]:
    """
    First order decorator to mark a method as the invocation method to be used for the command. Also enables
    dependency injection on the decorated method. The decorated method **must** have the first parameter (non-self)
    accepting an instance of :obj:`~lightbulb.context.Context`. Remaining parameters will attempt to be
    dependency injected.

    Args:
        func: The method to be marked as the command invocation method.

    Returns:
        The decorated method with dependency injection enabled.

    Example:

        .. code-block:: python

            class ExampleCommand(
                lightbulb.SlashCommand,
                name="example",
                description="example"
            ):
                @lightbulb.invoke
                async def invoke(self, ctx: lightbulb.Context) -> None:
                    await ctx.respond("example")

    Note:
        The command invocation function will never be called if any of the hooks for that command caused the pipeline
        to fail.
    """
    func = di.with_di(func)
    setattr(func, constants.COMMAND_INVOKE_METHOD_MARKER, "_")
    return func
