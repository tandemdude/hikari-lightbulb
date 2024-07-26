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
    "DI_ENABLED",
    "INJECTED",
    "Context",
    "Contexts",
    "DefaultContainer",
    "CommandContainer",
    "AutocompleteContainer",
    "ListenerContainer",
    "TaskContainer",
    "DependencyInjectionManager",
    "AutoInjecting",
    "with_di",
]

import collections
import contextlib
import contextvars
import inspect
import logging
import os
import sys
import typing as t

from lightbulb import utils
from lightbulb.di import container
from lightbulb.di import exceptions
from lightbulb.di import registry
from lightbulb.internal import marker

if t.TYPE_CHECKING:
    from lightbulb.internal import types

P = t.ParamSpec("P")
R = t.TypeVar("R")

DI_ENABLED: t.Final[bool] = os.environ.get("LIGHTBULB_DI_DISABLED", "false").lower() != "true"
DI_CONTAINER: contextvars.ContextVar[container.Container | None] = contextvars.ContextVar(
    "lb_di_container", default=None
)
LOGGER = logging.getLogger(__name__)

INJECTED: t.Final[t.Any] = marker.Marker("INJECTED")
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

Context = t.NewType("Context", str)
"""
Type representing a Lightbulb dependency injection context. Used for labelling containers so that they
can be accessed using method injection if required. You can create and use your own contexts by
creating an instance of this type.
"""


@t.final
class Contexts:
    """Collection of the dependency injection context values Lightbulb uses."""

    __slots__ = ()

    DEFAULT = Context("lightbulb.di.contexts.default")
    """The base DI context - all other contexts are built with this as the parent."""
    COMMAND = Context("lightbulb.di.contexts.command")
    """DI context used during command invocation, including for hooks and error handlers."""
    AUTOCOMPLETE = Context("lightbulb.di.contexts.autocomplete")
    """DI context used during autocomplete invocation."""
    LISTENER = Context("lightbulb.di.contexts.listener")
    """DI context used during listener invocation."""
    TASK = Context("lightbulb.di.contexts.task")
    """DI context used during task invocation."""


DefaultContainer = t.NewType("DefaultContainer", container.Container)
"""Injectable type representing the dependency container for the default context."""
CommandContainer = t.NewType("CommandContainer", container.Container)
"""Injectable type representing the dependency container for the command context."""
AutocompleteContainer = t.NewType("AutocompleteContainer", container.Container)
"""Injectable type representing the dependency container for the autocomplete context."""
ListenerContainer = t.NewType("ListenerContainer", container.Container)
"""Injectable type representing the dependency container for the listener context."""
TaskContainer = t.NewType("TaskContainer", container.Container)
"""Injectable type representing the dependency container for the task context."""

_CONTAINER_TYPE_BY_CONTEXT = {
    Contexts.DEFAULT: DefaultContainer,
    Contexts.COMMAND: CommandContainer,
    Contexts.AUTOCOMPLETE: AutocompleteContainer,
    Contexts.LISTENER: ListenerContainer,
    Contexts.TASK: TaskContainer,
}


class DependencyInjectionManager:
    """Class which contains dependency injection functionality."""

    __slots__ = ("_registries", "_default_container")

    def __init__(self) -> None:
        self._registries: dict[Context, registry.Registry] = collections.defaultdict(registry.Registry)
        self._default_container: container.Container | None = None

    @property
    def default_container(self) -> container.Container | None:
        """
        The container being used to provide dependencies for the :attr:`~Contexts.DEFAULT` context. This will
        be :obj:`None` until the first time any injection context is entered.
        """
        return self._default_container

    def registry_for(self, context: Context, /) -> registry.Registry:
        """
        Get the dependency registry for the given context. Creates one if necessary.

        Args:
            context: The injection context to get the registry for.

        Returns:
            The dependency registry for the given context.
        """
        return self._registries[context]

    @contextlib.asynccontextmanager
    async def enter_context(self, context: Context = Contexts.DEFAULT, /) -> t.AsyncIterator[container.Container]:
        """
        Context manager that ensures a dependency injection context is available for the nested operations.

        Args:
            context: The context to enter. If you are trying to enter a non-default (:obj:`~DiContext.DEFAULT`) context,
                the default context will be entered first to ensure its dependencies are available. Defaults to
                :obj:`~DiContext.DEFAULT`.

        Yields:
            :obj:`~lightbulb.di.container.Container`: The container that has been entered.

        Example:

            .. code-block:: python

                # Enter a specific context ('client' is your lightbulb.Client instance)
                with client.di.enter_context(lightbulb.di.DiContext.COMMAND):
                    await some_function_that_needs_dependencies()

        Warning:
            If you have disabled dependency injection using the ``LIGHTBULB_DI_DISABLED`` environment variable,
            this method will do nothing and the context manager will return :obj:`None`. Most users will never
            have to worry about this, but it is something to consider. The type-hint does not reflect this
            to prevent your type-checker complaining about not checking for :obj:`None`.
        """
        if DI_ENABLED:
            initial_token, initial = None, DI_CONTAINER.get(None)
            if initial is None:
                if self._default_container is None:
                    self._default_container = container.Container(self._registries[Contexts.DEFAULT])
                    self._default_container.add_value(DefaultContainer, self._default_container)

                initial_token = DI_CONTAINER.set(self._default_container)

            ctx_token: contextvars.Token[container.Container | None] | None = None
            if context != Contexts.DEFAULT:
                new_container = container.Container(self._registries[context], parent=DI_CONTAINER.get())
                new_container.add_value(_CONTAINER_TYPE_BY_CONTEXT[context], new_container)
                ctx_token = DI_CONTAINER.set(new_container)

            try:
                if (ct := DI_CONTAINER.get(None)) is not None:
                    async with ct:
                        yield ct
            finally:
                if ctx_token is not None:
                    DI_CONTAINER.reset(ctx_token)
                if initial_token is not None:
                    DI_CONTAINER.reset(initial_token)
        else:
            # I'm not sure how to deal with this - but I definitely don't want to hint the return type
            # as optional because that adds annoying assertions further down the line for users
            #
            # I think I should just account for this internally within the library and document the
            # behaviour - chances are almost all users will never come across this
            yield None  # type: ignore

    async def close(self) -> None:
        """
        Close the default dependency injection context. This **must** be called if you wish the teardown
        functions for any dependencies registered for the default registry to be called.

        Returns:
            :obj:`None`
        """
        if self._default_container is not None:
            await self._default_container.close()
            self._default_container = None


CANNOT_INJECT = object()


def _parse_injectable_params(func: t.Callable[..., t.Any]) -> tuple[list[tuple[str, t.Any]], dict[str, t.Any]]:
    positional_or_keyword_params: list[tuple[str, t.Any]] = []
    keyword_only_params: dict[str, t.Any] = {}

    parameters = inspect.signature(func, locals={"lightbulb": sys.modules["lightbulb"]}, eval_str=True).parameters
    for parameter in parameters.values():
        if (
            # If the parameter has no annotation
            parameter.annotation is inspect.Parameter.empty
            # If the parameter is not positional-or-keyword or keyword-only
            or parameter.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            # If it has a default that isn't INJECTED
            or ((default := parameter.default) is not inspect.Parameter.empty and default is not INJECTED)
        ):
            if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                positional_or_keyword_params.append((parameter.name, CANNOT_INJECT))
            continue

        if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
            positional_or_keyword_params.append((parameter.name, parameter.annotation))
        else:
            # It has to be a keyword-only parameter
            keyword_only_params[parameter.name] = parameter.annotation

    return positional_or_keyword_params, keyword_only_params


class AutoInjecting:
    """
    Wrapper for a callable that implements dependency injection. When called, resolves the required
    dependencies and calls the original callable. Supports both synchronous and asynchronous functions,
    however this cannot be called synchronously - synchronous functions will need to be awaited.

    You should generally never have to instantiate this yourself - you should instead use one of the
    decorators that applies this to the target automatically.

    See Also:
        :meth:`~with_di`
        :meth:`~lightbulb.commands.execution.hook`
        :meth:`~lightbulb.commands.execution.invoke`
    """

    __slots__ = ("_func", "_self", "_pos_or_kw_params", "_kw_only_params")

    def __init__(
        self,
        func: t.Callable[..., t.Awaitable[t.Any]],
        self_: t.Any = None,
        _cached_pos_or_kw_params: list[tuple[str, t.Any]] | None = None,
        _cached_kw_only_params: dict[str, t.Any] | None = None,
    ) -> None:
        self._func = func
        self._self: t.Any = self_

        if _cached_pos_or_kw_params is not None and _cached_kw_only_params is not None:
            self._pos_or_kw_params = _cached_pos_or_kw_params
            self._kw_only_params = _cached_kw_only_params
        else:
            self._pos_or_kw_params, self._kw_only_params = _parse_injectable_params(func)

    def __get__(self, instance: t.Any, _: type[t.Any]) -> AutoInjecting:
        if instance is not None:
            return AutoInjecting(self._func, instance, self._pos_or_kw_params, self._kw_only_params)
        return self

    def __getattr__(self, item: str) -> t.Any:
        return getattr(self._func, item)

    def __setattr__(self, key: str, value: t.Any) -> None:
        if key in self.__slots__:
            return super().__setattr__(key, value)

        setattr(self._func, key, value)

    async def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        new_kwargs: dict[str, t.Any] = {}
        new_kwargs.update(kwargs)

        di_container: container.Container | None = DI_CONTAINER.get(None)

        injectables = {
            name: type
            for name, type in self._pos_or_kw_params[len(args) + (self._self is not None) :]
            if name not in new_kwargs
        }
        injectables.update({name: type for name, type in self._kw_only_params.items() if name not in new_kwargs})

        for name, type in injectables.items():
            # Skip any arguments that we can't inject
            if type is CANNOT_INJECT:
                continue

            if di_container is None:
                raise exceptions.DependencyNotSatisfiableException("no DI context is available")

            new_kwargs[name] = await di_container.get(type)

        if self._self is not None:
            return await utils.maybe_await(self._func(self._self, *args, **new_kwargs))
        return await utils.maybe_await(self._func(*args, **new_kwargs))


def with_di(func: t.Callable[P, types.MaybeAwaitable[R]]) -> t.Callable[P, t.Awaitable[R]]:
    """
    Decorator that enables dependency injection on the decorated asynchronous function. If dependency injection
    has been disabled globally then this function does nothing and simply returns the object that was passed in.

    Args:
        func: The asynchronous function to enable dependency injection for.

    Returns:
        The function with dependency injection enabled, or the same function if DI has been disabled globally.

    Warning:
        Dependency injection relies on a context (note: not a lightbulb :obj:`~lightbulb.context.Context`) being
        available when the function is called. If the function is called during a lightbulb-controlled flow
        (such as command invocation or error handling), then one will be available automatically. Otherwise,
        you will have to set up the context yourself using the helper context manager
        :meth:`~DependencyInjectionManager.enter_context`.
    """
    if DI_ENABLED and not isinstance(func, AutoInjecting):
        return AutoInjecting(func)  # type: ignore[reportReturnType]
    return func  # type: ignore[reportReturnType]
