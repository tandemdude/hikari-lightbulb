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

__all__ = ["DependencyExpression", "If", "Try"]

import abc
import types
import typing as t

from lightbulb.di import exceptions
from lightbulb.di import utils as di_utils

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from lightbulb.di import container as container_

T = t.TypeVar("T")


class BaseCondition(abc.ABC):
    """
    Base class for dependency conditions. Implements ``|`` and ``[]`` operators in order to be used
    as a type hint, and combined with other elements in a type hint.
    """

    __slots__ = ("inner", "inner_id", "order")

    def __init__(self, inner: type[t.Any] | types.UnionType | tuple[t.Any, ...] | None) -> None:
        if isinstance(inner, tuple) or inner is None or t.get_origin(inner) in (types.UnionType, t.Union):
            raise SyntaxError("{self.__class__.__name__!r} can only be parameterized by concrete types")

        self.inner: type[t.Any] = inner  # type: ignore[reportAttributeAccessIssue]
        self.inner_id: str = di_utils.get_dependency_id(inner)

        self.order: list[t.Any] = [self]

    def __class_getitem__(cls, item: t.Any) -> BaseCondition:
        return cls(item)

    def __or__(self, other: t.Any) -> BaseCondition:
        if t.get_origin(other) in (types.UnionType, t.Union):
            self.order = [*self.order, *t.get_args(other)]
        else:
            self.order.append(other)
        return self

    def __ror__(self, other: t.Any) -> BaseCondition:
        if t.get_origin(other) in (types.UnionType, t.Union):
            self.order = [*t.get_args(other), *self.order]
        else:
            self.order.insert(0, other)
        return self

    def __repr__(self) -> str:
        includes_none: bool = False
        parts: list[str] = []
        for item in self.order:
            if item is None:
                includes_none = True
            elif item is self:
                parts.append(f"{self.__class__.__name__}[{self.inner_id}]")
            else:
                parts.append(repr(item) if isinstance(item, BaseCondition) else di_utils.get_dependency_id(item))

        if includes_none:
            parts.append("None")

        return " | ".join(parts)

    @abc.abstractmethod
    async def _get_from(self, container: container_.Container) -> tuple[bool, t.Any]: ...


class If(BaseCondition):
    """
    Dependency injection condition that will only fall back when the requested
    dependency is not known to the current container. This is the default when
    no condition is specified.

    Example:

        .. code-block:: python

            @lightbulb.di.with_di
            async def foo(bar: If[Bar] | None) -> None:
                # The 'bar' parameter will be 'None' if the 'Bar' dependency
                # is unregistered.
                ...

            # Lightbulb treats the lack of meta annotation as meaning the same as 'If[dep]'
            @lightbulb.di.with_di
            async def foo(bar: Bar | None) -> None:
                # Same as previous example
                ...
    """

    __slots__ = ()

    async def _get_from(self, container: container_.Container) -> tuple[bool, t.Any]:
        if self.inner_id in container:
            return True, await container._get(self.inner_id)
        return False, None


class Try(BaseCondition):
    """
    Dependency injection condition that will fall back when the requested dependency
    is either unknown to the current container, or creation raises an exception.

    Example:

        .. code-block:: python

            @lightbulb.di.with_di
            async def foo(bar: Try[Bar] | None) -> None:
                # The 'bar' parameter will be 'None' if creating the 'Bar' dependency
                # failed, or is unregistered.
                ...
    """

    __slots__ = ()

    async def _get_from(self, container: container_.Container) -> tuple[bool, t.Any]:
        try:
            return True, await container._get(self.inner_id)
        except exceptions.DependencyInjectionException:
            return False, None


class DependencyExpression(t.Generic[T]):
    """
    A cached dependency expression. This contains the steps needed to resolve the dependencies
    for a single function parameter.

    Args:
        order: The sequence of conditions required to resolve the dependency expression.
        required: Whether the dependency expression is required - i.e. can resolve to ``None``.
    """

    __slots__ = ("_order", "_required")

    def __init__(self, order: Sequence[BaseCondition], required: bool) -> None:
        self._order = order
        self._required = required

    def __repr__(self) -> str:
        return f"DependencyExpression({self._order}, required={self._required})"

    async def resolve(self, container: container_.Container, /) -> T | None:
        """
        Resolve the dependency that satisfies this expression from the given container.

        Args:
            container: The container to use while satisfying the expression.

        Returns:
            The resolved dependency, or ``None`` if the dependency could not be resolved, and ``required`` was
            ``True`` upon creation.
        """
        if len(self._order) == 1 and self._required:
            return await container._get(self._order[0].inner_id)

        for dependency in self._order:
            succeeded, found = await dependency._get_from(container)
            if succeeded:
                return found

        if not self._required:
            return None

        raise exceptions.DependencyNotSatisfiableException("no dependencies can satisfy the requested type")

    # TODO - TypeExpr
    @classmethod
    def create(cls, expr: t.Any, /) -> DependencyExpression[t.Any]:
        """
        Create a dependency expression from a type expression (type hint).

        Args:
            expr: The type expression to create the dependency expression from.

        Returns:
            The created dependency expression.
        """
        requested_dependencies: list[BaseCondition] = []
        required: bool = True

        args: Sequence[t.Any] = (expr,)
        if t.get_origin(expr) in (types.UnionType, t.Union):
            args = t.get_args(expr)
        elif isinstance(expr, BaseCondition):
            args = expr.order

        for arg in args:
            if arg is types.NoneType or arg is None:
                required = False
                continue

            if not isinstance(arg, BaseCondition):
                # a concrete type T implicitly means If[T]
                arg = If(arg)

            requested_dependencies.append(arg)

        return cls(requested_dependencies, required)


if t.TYPE_CHECKING:
    If = t.Annotated[T, None]  # type: ignore[reportAssignmentType]
    Try = t.Annotated[T, None]  # type: ignore[reportAssignmentType]
