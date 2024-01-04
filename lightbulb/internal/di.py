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

import inspect
import typing as t

import typing_extensions as t_ex

from lightbulb import context

if t.TYPE_CHECKING:
    from lightbulb import client as client_

AnyCallableT = t.TypeVar("AnyCallableT", bound=t.Callable[..., t.Any])


def find_injectable_kwargs(func: t.Callable[..., t.Any]) -> t.Dict[str, t.Any]:
    parameters = inspect.signature(func, eval_str=True).parameters

    injectable_parameters: t.List[inspect.Parameter] = []
    for parameter in parameters.values():
        if (
            parameter.annotation is inspect.Parameter.empty
            and parameter.default is inspect.Parameter.empty
            and parameter.kind is not inspect.Parameter.POSITIONAL_ONLY
        ):
            continue

        if issubclass(parameter.annotation, context.Context) or parameter.annotation is t_ex.Self:  # type: ignore[reportUnknownMemberType]
            continue

        injectable_parameters.append(parameter)

    injectable: t.Dict[str, t.Any] = {}
    for parameter in injectable_parameters:
        injectable[parameter.name] = parameter.annotation

    return injectable


class LazyInjecting:
    __slots__ = ("_func", "_processed", "_client", "_injectables", "_self", "__command_hook_type__")

    def __init__(
        self,
        func: t.Callable[..., t.Awaitable[t.Any]],
        injectables: t.Optional[t.Dict[str, t.Any]] = None,
        self_: t.Any = None,
        client: t.Optional[client_.Client] = None,
    ) -> None:
        self._func = func
        self._injectables: t.Optional[t.Dict[str, t.Any]] = injectables
        self._self: t.Any = self_
        self._client: t.Optional[client_.Client] = client

    def __get__(self, instance: t.Any, owner: t.Type[t.Any]) -> LazyInjecting:
        if instance is not None:
            return LazyInjecting(self._func, self._injectables, instance, self._client)
        return self

    async def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        new_kwargs: t.Dict[str, t.Any] = {}
        new_kwargs.update(kwargs)

        if self._client is None:
            raise RuntimeError("cannot prepare dependency injection as client not yet populated")

        if self._injectables is None:
            self._injectables = find_injectable_kwargs(self._func)

        for name, type in self._injectables.items():
            new_kwargs[name] = await self._client._di_container.aget(type)

        if self._self is not None:
            return await self._func(self._self, *args, **new_kwargs)
        return await self._func(*args, **new_kwargs)
