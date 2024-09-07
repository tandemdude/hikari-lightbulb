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

__all__ = ["If", "Try"]

import abc
import types
import typing as t

from lightbulb.di import exceptions
from lightbulb.di import utils as di_utils

if t.TYPE_CHECKING:
    from lightbulb.di import container as container_

T = t.TypeVar("T")


class BaseCondition(abc.ABC):
    __slots__ = ("inner", "inner_id", "order")

    def __init__(self, inner: type[t.Any] | types.UnionType | tuple[t.Any, ...]) -> None:
        if isinstance(inner, (types.UnionType, tuple)):
            raise SyntaxError("{self.__class__.__name__!r} can only be parameterized by concrete types")

        self.inner: type[t.Any] = inner
        self.inner_id: str = di_utils.get_dependency_id(inner)

        self.order: list[t.Any] = [self]

    def __class_getitem__(cls, item: t.Any) -> BaseCondition:
        return cls(item)

    def __or__(self, other: t.Any) -> BaseCondition:
        if isinstance(other, types.UnionType):
            self.order = [*self.order, *t.get_args(other)]
        else:
            self.order.append(other)
        return self

    def __ror__(self, other: t.Any) -> BaseCondition:
        if isinstance(other, types.UnionType):
            self.order = [*t.get_args(other), *self.order]
        else:
            self.order.insert(0, other)
        return self

    def __repr__(self) -> str:
        parts: list[str] = []
        for item in self.order:
            if item is None:
                parts.append("None")
            elif item is self:
                parts.append(f"{self.__class__.__name__}[{self.inner_id}]")
            else:
                parts.append(repr(item) if isinstance(item, BaseCondition) else di_utils.get_dependency_id(item))

        return " | ".join(parts)

    @abc.abstractmethod
    async def _get_from(self, container: container_.Container) -> tuple[bool, t.Any]: ...


class If(BaseCondition):
    """
    Dependency injection condition that will only fall back when the requested
    dependency is not known to the current container. This is the default when
    no condition is specified.
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
    """

    __slots__ = ()

    async def _get_from(self, container: container_.Container) -> tuple[bool, t.Any]:
        try:
            return True, await container._get(self.inner_id)
        except exceptions.DependencyInjectionException:
            return False, None


if t.TYPE_CHECKING:
    If = t.Annotated[T, None]  # type: ignore[reportAssignmentType]
    Try = t.Annotated[T, None]  # type: ignore[reportAssignmentType]
