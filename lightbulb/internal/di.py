# -*- coding: utf-8 -*-
# Copyright © tandemdude 2023-present
#
# This file is part of Lightbulb.
#
# Lightbulb is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Lightbulb is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Lightbulb. If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

import contextlib
import contextvars
import inspect
import os
import typing as t

import svcs

T = t.TypeVar("T")
AnyAsyncCallableT = t.TypeVar("AnyAsyncCallableT", bound=t.Callable[..., t.Awaitable[t.Any]])


DI_ENABLED: t.Final[bool] = os.environ.get("LIGHTBULB_DI_DISABLED", "false").lower() == "true"
DI_CONTAINER: contextvars.ContextVar[svcs.Container] = contextvars.ContextVar("_di_container")


class DependencyInjectionManager:
    """Class which contains dependency injection functionality - intended to be used with composition."""

    __slots__ = ("_di_registry", "_di_container")

    def __init__(self) -> None:
        self._di_registry: svcs.Registry = svcs.Registry()
        self._di_container: t.Optional[svcs.Container] = None

    @property
    def di_registry(self) -> svcs.Registry:
        """The dependency injection registry containing dependencies available for this instance."""
        return self._di_registry

    @property
    def di_container(self) -> svcs.Container:
        """The dependency injection container used for this instance. Lazily instantiated."""
        if self._di_container is None:
            self._di_container = svcs.Container(self.di_registry)
        return self._di_container

    def register_dependency(self, type: t.Type[T], factory: t.Callable[[], t.Union[t.Awaitable[T], T]]) -> None:
        """
        Register a dependency as usable by dependency injection. All dependencies are considered to be
        singletons, meaning the factory will always be called at most once.

        Args:
            type (:obj:`~typing.Type` [ ``T`` ]): The type of the dependency to register.
            factory: The factory function to use to provide the dependency value.

        Returns:
            :obj:`None`
        """
        self.di_registry.register_factory(type, factory)  # type: ignore[reportUnknownMemberType]


@contextlib.contextmanager
def ensure_di_context(client: DependencyInjectionManager) -> t.Generator[None, t.Any, t.Any]:
    """
    Context manager that ensures a dependency injection context is available for the nested operations.

    Args:
        client (:obj:`~DependencyInjectionAware`): The client that is aware of the required information to be
            able to supply dependencies for injection.

    Example:

        .. code-block:: python

            with lightbulb.ensure_di_context(client):
                await some_function_that_needs_dependencies()
    """
    if DI_ENABLED:
        token = DI_CONTAINER.set(client.di_container)
        try:
            yield
        finally:
            DI_CONTAINER.reset(token)
    else:
        yield


def find_injectable_kwargs(
    func: t.Callable[..., t.Any], passed_args: int, passed_kwargs: t.Collection[str]
) -> t.Dict[str, t.Any]:
    """
    Given a function, parse the signature to discover which parameters are suitable for dependency injection.

    A parameter is suitable for dependency injection if:

    - It has a type annotation

    - It has no default value

    - It is not positional-only (injected parameters are always passed as a keyword argument)

    Args:
        func: The function to discover the dependency injection suitable parameters for.
        passed_args (:obj:`int`): The number of positional arguments passed to the function in this invocation.
        passed_kwargs (:obj:`~typing.Collection` [ :obj:`str` ]): The names of all the keyword arguments passed
            to the function in this invocation.

    Returns:
        :obj:`~typing.Dict` [ :obj:`str`, :obj:`~typing.Any` ]: Mapping of parameter name to parameter annotation
            value for parameters that are suitable for dependency injection.
    """
    parameters = inspect.signature(func, eval_str=True).parameters

    injectable_parameters: t.Dict[str, t.Any] = {}
    for parameter in [*parameters.values()][passed_args:]:
        # Injectable parameters MUST have an annotation and no default
        if (
            parameter.annotation is inspect.Parameter.empty
            or parameter.default is not inspect.Parameter.empty
            # Injecting positional only parameters is far too annoying
            or parameter.kind is inspect.Parameter.POSITIONAL_ONLY
            # If a kwarg has been passed then we don't want to replace it
            or parameter.name in passed_kwargs
        ):
            continue

        injectable_parameters[parameter.name] = parameter.annotation

    return injectable_parameters


class LazyInjecting:
    """
    Wrapper for a callable that implements dependency injection. When called, resolves the required
    dependencies and calls the original callable. Only supports asynchronous functions.

    You should generally never have to instantiate this yourself - you should instead use one of the
    decorators that applies this to the target automatically.

    See Also:
        :obj:`~with_di`
        :obj:`~lightbulb.commands.execcution.hook`
        :obj:`~lightbulb.commands.execution.invoke`
    """

    __slots__ = ("_func", "_processed", "_self")

    def __init__(
        self,
        func: t.Callable[..., t.Awaitable[t.Any]],
        self_: t.Any = None,
    ) -> None:
        self._func = func
        self._self: t.Any = self_

    def __get__(self, instance: t.Any, owner: t.Type[t.Any]) -> LazyInjecting:
        if instance is not None:
            return LazyInjecting(self._func, instance)
        return self

    def __getattr__(self, item: str) -> t.Any:
        return getattr(self._func, item)

    def __setattr__(self, key: str, value: t.Any) -> None:
        setattr(self._func, key, value)

    async def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        new_kwargs: t.Dict[str, t.Any] = {}
        new_kwargs.update(kwargs)

        di_container: t.Optional[svcs.Container] = DI_CONTAINER.get(None)
        if di_container is None:
            raise RuntimeError("cannot prepare dependency injection as no DI context is available")

        injectables = find_injectable_kwargs(self._func, len(args) + (self._self is not None), set(kwargs.keys()))

        for name, type in injectables.items():
            new_kwargs[name] = await di_container.aget(type)

        if self._self is not None:
            return await self._func(self._self, *args, **new_kwargs)
        return await self._func(*args, **new_kwargs)


def with_di(func: AnyAsyncCallableT) -> AnyAsyncCallableT:
    """
    Enables dependency injection on the decorated asynchronous function. If dependency injection
    has been disabled globally then this function does nothing and simply returns the object that was passed in.

    Args:
        func: The asynchronous function to enable dependency injection for

    Returns:
        The function with dependency injection enabled, or the same function if DI has been disabled globally.

    Warning:
        Dependency injection relies on a context (note: not a lightbulb :obj:`~lightbulb.context.Context`) being
        available when the function is called. If the function is called during a lightbulb-controlled flow
        (such as command invocation or error handling), then one will be available automatically. Otherwise,
        you will have to set up the context yourself using the helper context manager :obj:`~setup_di_context`.
    """
    if DI_ENABLED:
        return LazyInjecting(func)  # type: ignore[reportReturnType]
    return func
