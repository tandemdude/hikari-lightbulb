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

__all__ = ["Registry"]

import typing as t

import networkx as nx

from lightbulb.di import exceptions
from lightbulb.di import utils as di_utils

if t.TYPE_CHECKING:
    from lightbulb.di import container
    from lightbulb.internal import types

T = t.TypeVar("T")


class Registry:
    """
    A dependency registry containing information about how to create the registered dependencies.

    You can use ``in`` to check if a dependency has been registered to this registry.

    Example:

        .. code-block:: python

            >>> registry = lightbulb.di.Registry()
            >>> object in registry
            False
            >>> registry.register_value(object, object())
            >>> object in registry
            True

    Note:
        When containers are created for a registry, the registry is frozen to prevent additional dependencies
        being registered. The registry is unfrozen once all containers providing from a registry have been closed.
    """

    __slots__ = ("_graph", "_active_containers")

    def __init__(self) -> None:
        self._graph: nx.DiGraph[str] = nx.DiGraph()
        self._active_containers: set[container.Container] = set()

    def __contains__(self, item: type[t.Any]) -> bool:
        dep_id = di_utils.get_dependency_id(item)
        if dep_id not in self._graph:
            return False

        return self._graph.nodes[dep_id].get("factory") is not None

    def _freeze(self, cnt: container.Container) -> None:
        self._active_containers.add(cnt)

    def _unfreeze(self, cnt: container.Container) -> None:
        self._active_containers.remove(cnt)

    def register_value(
        self,
        typ: type[T],
        value: T,
        *,
        teardown: t.Callable[[T], types.MaybeAwaitable[None]] | None = None,
    ) -> None:
        """
        Registers a pre-existing value as a dependency.

        Args:
            typ: The type to register the dependency as.
            value: The value to use for the dependency.
            teardown: The teardown function to be called when the container is closed. Teardown functions
                must take exactly one argument - the dependency that is being torn down. Defaults to :obj:`None`.

        Returns:
            :obj:`None`

        Raises:
            :obj:`lightbulb.di.exceptions.RegistryFrozenException`: If the registry is frozen.
        """
        self.register_factory(typ, lambda: value, teardown=teardown)

    def register_factory(
        self,
        typ: type[T],
        factory: t.Callable[..., types.MaybeAwaitable[T]],
        *,
        teardown: t.Callable[[T], types.MaybeAwaitable[None]] | None = None,
    ) -> None:
        """
        Registers a factory for creating a dependency.

        Args:
            typ: The type to register the dependency as.
            factory: The factory used to create the dependency. A factory method may take any number of parameters.
                The parameters will all attempt to be dependency-injected when creating the dependency. Any default
                parameter values will be ignored.
            teardown: The teardown function to be called when the container is closed. Teardown functions
                must take exactly one argument - the dependency that is being torn down. Defaults to :obj:`None`.

        Returns:
            :obj:`None`

        Raises:
            :obj:`lightbulb.di.exceptions.RegistryFrozenException`: If the registry is frozen.
            :obj:`lightbulb.di.exceptions.CircularDependencyException`: If the factory requires itself as a dependency.
        """
        if self._active_containers:
            raise exceptions.RegistryFrozenException

        dependency_id = di_utils.get_dependency_id(typ)

        # We are overriding a previously defined dependency and want to strip the edges, so we don't have
        # a load of redundant ones - maybe the new version doesn't require the same sub-dependencies
        if dependency_id in self._graph:
            self._graph.remove_edges_from(list(self._graph.out_edges(dependency_id)))

        factory_dependencies = di_utils.resolve_dependency_id_for_all_parameters(factory)

        if dependency_id in factory_dependencies:
            raise exceptions.CircularDependencyException(f"factory for type {typ!r} requires itself as a dependency")

        di_utils.populate_graph_for_dependency(self._graph, dependency_id, factory, teardown)
