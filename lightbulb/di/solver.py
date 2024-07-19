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

__all__ = ["DI_ENABLED", "INJECTED", "DiContext", "DependencyInjectionManager", "LazyInjecting", "with_di"]

import collections
import contextlib
import contextvars
import enum
import inspect
import logging
import os
import typing as t

from lightbulb.di import container
from lightbulb.di import registry

T = t.TypeVar("T")
AnyAsyncCallableT = t.TypeVar("AnyAsyncCallableT", bound=t.Callable[..., t.Awaitable[t.Any]])

DI_ENABLED: t.Final[bool] = os.environ.get("LIGHTBULB_DI_DISABLED", "false").lower() != "true"
DI_CONTAINER: contextvars.ContextVar[container.Container | None] = contextvars.ContextVar(
    "lb_di_container", default=None
)
LOGGER = logging.getLogger(__name__)

INJECTED: t.Final[t.Any] = object()
"""
Flag value used to explicitly mark that a function parameter should be dependency-injected.

This exists to stop type checkers complaining that function arguments are not provided when calling
dependency-injection enabled functions.

Example:

    .. code-block:: python

        @lightbulb.di.with_di
        async def foo(bar: SomeClass = lightbulb.INJECTED) -> None:
            ...

        # Type-checker shouldn't error that a parameter is missing
        await foo()
"""


class DiContext(enum.Enum):
    DEFAULT = enum.auto()
    COMMAND = enum.auto()
    LISTENER = enum.auto()
    TASK = enum.auto()


class DependencyInjectionManager:
    """Class which contains dependency injection functionality."""

    __slots__ = ("_registries", "_base_container")

    def __init__(self) -> None:
        self._registries: dict[DiContext, registry.Registry] = collections.defaultdict(registry.Registry)
        self._base_container: container.Container | None = None

    def registry_for(self, context: DiContext, /) -> registry.Registry:
        """The dependency injection registry containing dependencies available for this instance."""
        return self._registries[context]

    @contextlib.asynccontextmanager
    async def enter_context(self, context: DiContext, /) -> t.AsyncIterator[None]:
        #     """
        #     Context manager that ensures a dependency injection context is available for the nested operations.
        #
        #     Args:
        #         manager: The DI manager to use to supply dependencies for this injection context.
        #
        #     Example:
        #
        #         .. code-block:: python
        #
        #             with lightbulb.ensure_di_context(client):
        #                 await some_function_that_needs_dependencies()
        #     """
        if context is DiContext.DEFAULT:
            raise ValueError("cannot explicitly enter default context")

        if DI_ENABLED:
            initial_token, initial = None, DI_CONTAINER.get(None)
            if initial is None:
                if self._base_container is None:
                    self._base_container = container.Container(self._registries[DiContext.DEFAULT])
                initial_token = DI_CONTAINER.set(self._base_container)

            new_container = container.Container(self._registries[context], parent=DI_CONTAINER.get())
            token = DI_CONTAINER.set(new_container)

            try:
                async with new_container:
                    yield
            finally:
                DI_CONTAINER.reset(token)
                if initial_token is not None:
                    DI_CONTAINER.reset(initial_token)
        else:
            yield


def find_injectable_kwargs(
    func: t.Callable[..., t.Any], passed_args: int, passed_kwargs: t.Collection[str]
) -> dict[str, t.Any]:
    """
    Given a function, parse the signature to discover which parameters are suitable for dependency injection.

    A parameter is suitable for dependency injection if:

    - It has a type annotation

    - It has no default value (unless the default value is :obj:`~INJECTED`).

    - It is not positional-only (injected parameters are always passed as a keyword argument)

    Args:
        func: The function to discover the dependency injection suitable parameters for.
        passed_args: The number of positional arguments passed to the function in this invocation.
        passed_kwargs: The names of all the keyword arguments passed
            to the function in this invocation.

    Returns:
        Mapping of parameter name to parameter annotation value for parameters that are suitable for
        dependency injection.
    """
    parameters = inspect.signature(func, eval_str=True).parameters

    injectable_parameters: dict[str, t.Any] = {}
    for parameter in [*parameters.values()][passed_args:]:
        # Injectable parameters MUST have an annotation and no default
        if (
            parameter.annotation is inspect.Parameter.empty
            or ((default := parameter.default) is not inspect.Parameter.empty and default is not INJECTED)
            # Injecting positional only parameters is far too annoying
            or parameter.kind is inspect.Parameter.POSITIONAL_ONLY
            # If a kwarg has been passed then we don't want to replace it
            or parameter.name in passed_kwargs
        ):
            continue

        injectable_parameters[parameter.name] = parameter.annotation

    return injectable_parameters


class LazyInjecting:
    # TODO - cache dependency mapping for parameters
    """
    Wrapper for a callable that implements dependency injection. When called, resolves the required
    dependencies and calls the original callable. Only supports asynchronous functions.

    You should generally never have to instantiate this yourself - you should instead use one of the
    decorators that applies this to the target automatically.

    See Also:
        :obj:`~with_di`
        :obj:`~lightbulb.commands.execution.hook`
        :obj:`~lightbulb.commands.execution.invoke`
    """

    __slots__ = ("_func", "_self")

    def __init__(
        self,
        func: t.Callable[..., t.Awaitable[t.Any]],
        self_: t.Any = None,
    ) -> None:
        self._func = func
        self._self: t.Any = self_

    def __get__(self, instance: t.Any, owner: type[t.Any]) -> LazyInjecting:
        if instance is not None:
            return LazyInjecting(self._func, instance)
        return self

    def __getattr__(self, item: str) -> t.Any:
        return getattr(self._func, item)

    def __setattr__(self, key: str, value: t.Any) -> None:
        if key in ("_func", "_self"):
            return super().__setattr__(key, value)

        setattr(self._func, key, value)

    async def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        new_kwargs: dict[str, t.Any] = {}
        new_kwargs.update(kwargs)

        di_container: t.Optional[container.Container] = DI_CONTAINER.get(None)
        if di_container is None:
            raise RuntimeError("cannot prepare dependency injection as no DI context is available")

        injectables = find_injectable_kwargs(self._func, len(args) + (self._self is not None), set(kwargs.keys()))

        for name, type in injectables.items():
            new_kwargs[name] = await di_container.get(type)

        if self._self is not None:
            return await self._func(self._self, *args, **new_kwargs)
        return await self._func(*args, **new_kwargs)


def with_di(func: AnyAsyncCallableT) -> AnyAsyncCallableT:
    """
    Enables dependency injection on the decorated asynchronous function. If dependency injection
    has been disabled globally then this function does nothing and simply returns the object that was passed in.

    Args:
        func: The asynchronous function to enable dependency injection for.

    Returns:
        The function with dependency injection enabled, or the same function if DI has been disabled globally.

    Warning:
        Dependency injection relies on a context (note: not a lightbulb :obj:`~lightbulb.context.Context`) being
        available when the function is called. If the function is called during a lightbulb-controlled flow
        (such as command invocation or error handling), then one will be available automatically. Otherwise,
        you will have to set up the context yourself using the helper context manager :obj:`~setup_di_context`.
    """
    if DI_ENABLED and not isinstance(func, LazyInjecting):
        return LazyInjecting(func)  # type: ignore[reportReturnType]
    return func  # type: ignore[reportReturnType]
