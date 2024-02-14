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
import inspect
import typing as t

from lightbulb import exceptions
from lightbulb.internal import di

if t.TYPE_CHECKING:
    import typing_extensions as t_ex

    from lightbulb import context as context_

__all__ = ["ExecutionStep", "ExecutionSteps", "ExecutionHook", "ExecutionPipeline", "hook", "invoke"]

ExecutionHookFuncT: t_ex.TypeAlias = t.Callable[
    ["ExecutionPipeline", "context_.Context"], t.Union[t.Awaitable[None], None]
]


@dataclasses.dataclass(frozen=True, slots=True, eq=True)
class ExecutionStep:
    name: str


class ExecutionSteps:
    __slots__ = ()

    MAX_CONCURRENCY = ExecutionStep("MAX_CONCURRENCY")
    CHECKS = ExecutionStep("CHECKS")
    COOLDOWNS = ExecutionStep("COOLDOWNS")


@dataclasses.dataclass(frozen=True, slots=True, eq=True)
class ExecutionHook:
    step: ExecutionStep
    func: ExecutionHookFuncT

    async def __call__(self, pipeline: ExecutionPipeline, context: context_.Context) -> None:
        maybe_await = self.func(pipeline, context)
        if inspect.isawaitable(maybe_await):
            await maybe_await


class ExecutionPipeline:
    __slots__ = ("_context", "_remaining", "_hooks", "_current_step", "_current_hook", "_failures", "_abort")

    def __init__(self, context: context_.Context, order: t.Sequence[ExecutionStep]) -> None:
        self._context = context
        self._remaining = list(order)

        self._hooks: t.Dict[ExecutionStep, t.List[ExecutionHook]] = collections.defaultdict(list)
        for hook in context.command_data.hooks:
            self._hooks[hook.step].append(hook)

        self._current_step: t.Optional[ExecutionStep] = None
        self._current_hook: t.Optional[ExecutionHook] = None

        self._failures: t.Dict[
            ExecutionStep, t.List[exceptions.ExecutionHookFailedException]
        ] = collections.defaultdict(list)
        self._abort: t.Optional[exceptions.ExecutionHookFailedException] = None

    @property
    def failed(self) -> bool:
        return bool(self._failures) or self._abort is not None

    @property
    def aborted(self) -> bool:
        return self._abort is not None

    def _next_step(self) -> t.Optional[ExecutionStep]:
        if self._remaining:
            return self._remaining.pop(0)
        return None

    async def _run(self) -> None:
        print(self._hooks)

        self._current_step = self._next_step()
        print(self._current_step)
        while self._current_step is not None and not self.aborted:
            step_hooks = list(self._hooks.get(self._current_step, []))
            print(step_hooks)
            while step_hooks and not self.aborted:
                self._current_hook = step_hooks.pop(0)
                try:
                    await self._current_hook(self, self._context)
                except Exception as e:
                    self.fail(e)

            if self.failed:
                break

            self._current_step = self._next_step()

        if self.failed:
            causes = [failure for step_failures in self._failures.values() for failure in step_failures]
            if self._abort is not None:
                causes.append(self._abort)

            assert self._current_step is not None
            raise exceptions.ExecutionFailedException(causes, self._abort is not None, self._current_step)

        await getattr(self._context.command, self._context.command_data.invoke_method)(self._context)

    def fail(self, exc: t.Union[str, Exception], abort: bool = False) -> None:
        if not isinstance(exc, Exception):
            exc = RuntimeError(exc)

        assert self._current_step is not None
        assert self._current_hook is not None

        hook_exc = exceptions.ExecutionHookFailedException(self._current_hook, exc)

        if abort:
            self._abort = hook_exc
            return

        self._failures[self._current_step].append(hook_exc)


# TODO - add di to hook functions
def hook(step: ExecutionStep) -> t.Callable[[ExecutionHookFuncT], ExecutionHook]:
    def inner(func: ExecutionHookFuncT) -> ExecutionHook:
        return ExecutionHook(step, func)

    return inner


def invoke(func: t.Callable[..., t.Awaitable[t.Any]]) -> t.Callable[[context_.Context], t.Awaitable[t.Any]]:
    if not isinstance(func, di.LazyInjecting):
        func = di.LazyInjecting(func)

    setattr(func, "__lb_cmd_invoke_method__", "_")
    return func
