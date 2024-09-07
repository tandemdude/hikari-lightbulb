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

__all__ = ["Container", "DependencyExpression"]

import logging
import types
import typing as t

import networkx as nx

from lightbulb import utils
from lightbulb.di import conditions
from lightbulb.di import exceptions
from lightbulb.di import registry as registry_
from lightbulb.di import utils as di_utils

if t.TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

    from lightbulb.di import solver
    from lightbulb.internal import types as lb_types

T = t.TypeVar("T")

LOGGER = logging.getLogger(__name__)


class DependencyExpression(t.Generic[T]):
    __slots__ = ("_order", "_required")

    def __init__(self, order: Sequence[conditions.BaseCondition], required: bool) -> None:
        self._order = order
        self._required = required

    def __repr__(self) -> str:
        return f"DependencyExpression({self._order}, required={self._required})"

    async def resolve(self, container: Container, /) -> T | None:
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
        requested_dependencies: list[conditions.BaseCondition] = []
        required: bool = True

        args = expr.order if isinstance(expr, conditions.BaseCondition) else (t.get_args(expr) or (expr,))
        for arg in args:
            if arg is types.NoneType or arg is None:
                required = False
                continue

            if not isinstance(arg, conditions.BaseCondition):
                # a concrete type T implicitly means If[T]
                arg = conditions.If(arg)

            requested_dependencies.append(arg)

        return cls(requested_dependencies, required)


class Container:
    """
    A container for managing and supplying dependencies.

    Args:
        registry: The registry of dependencies supply-able by this container.
        parent: The parent container. Defaults to None.
    """

    __slots__ = ("_closed", "_graph", "_instances", "_parent", "_registry", "_tag")

    def __init__(
        self, registry: registry_.Registry, *, parent: Container | None = None, tag: solver.Context | None = None
    ) -> None:
        self._registry = registry
        self._registry._freeze(self)

        self._parent = parent
        self._tag = tag

        self._closed = False

        self._graph: nx.DiGraph[str] = nx.DiGraph(self._registry._graph)
        self._instances: dict[str, t.Any] = {}

        self.add_value(Container, self)

    def __repr__(self) -> str:
        return f"<lightbulb.di.container.Container tag={self._tag!r}>"

    def __contains__(self, item: t.Any) -> bool:
        if not isinstance(item, str):
            item = di_utils.get_dependency_id(item)

        if item in self._instances:
            return True

        node = self._graph.nodes.get(item)
        if node is not None and node.get("factory") is not None:
            return True

        if self._parent is None:
            return False

        return item in self._parent

    async def __aenter__(self) -> Container:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException], exc_val: BaseException, exc_tb: types.TracebackType
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Closes the container, running teardown procedures for each created dependency belonging to this container."""
        for dependency_id, instance in self._instances.items():
            if (td := self._graph.nodes[dependency_id]["teardown"]) is None:
                continue

            await utils.maybe_await(td(instance))

        self._registry._unfreeze(self)
        self._closed = True

    def add_factory(
        self,
        typ: type[T],
        factory: Callable[..., lb_types.MaybeAwaitable[T]],
        *,
        teardown: Callable[[T], lb_types.MaybeAwaitable[None]] | None = None,
    ) -> None:
        """
        Adds the given factory as an ephemeral dependency to this container. This dependency is only accessible
        from contexts including this container and will be cleaned up when the container is closed.

        Args:
            typ: The type to register the dependency as.
            factory: The factory used to create the dependency.
            teardown: The teardown function to be called when the container is closed. Defaults to :obj:`None`.

        Returns:
            :obj:`None`

        See Also:
            :meth:`lightbulb.di.registry.Registry.register_factory` for factory and teardown function spec.
        """
        dependency_id = di_utils.get_dependency_id(typ)

        if dependency_id in self._graph:
            self._graph.remove_edges_from(list(self._graph.out_edges(dependency_id)))
        di_utils.populate_graph_for_dependency(self._graph, dependency_id, factory, teardown, container=self)

    def add_value(
        self,
        typ: type[T],
        value: T,
        *,
        teardown: Callable[[T], lb_types.MaybeAwaitable[None]] | None = None,
    ) -> None:
        """
        Adds the given value as an ephemeral dependency to this container. This dependency is only accessible
        from contexts including this container and will be cleaned up when the container is closed.

        Args:
            typ: The type to register the dependency as.
            value: The value to use for the dependency.
            teardown: The teardown function to be called when the container is closed. Defaults to :obj:`None`.

        Returns:
            :obj:`None`

        See Also:
            :meth:`lightbulb.di.registry.Registry.register_value` for teardown function spec.
        """
        dependency_id = di_utils.get_dependency_id(typ)
        self._instances[dependency_id] = value

        if dependency_id in self._graph:
            self._graph.remove_edges_from(list(self._graph.out_edges(dependency_id)))
        self._graph.add_node(dependency_id, factory=lambda: None, teardown=teardown)

    async def _get(self, dependency_id: str) -> t.Any:
        if self._closed:
            raise exceptions.ContainerClosedException("the container is closed")

        # TODO - look into whether locking is necessary - how likely are we to have race conditions
        if (existing := self._instances.get(dependency_id)) is not None:
            return existing

        if (data := self._graph.nodes.get(dependency_id)) is None or data.get("factory") is None:
            if self._parent is None:
                raise exceptions.DependencyNotSatisfiableException(
                    f"cannot create dependency {dependency_id!r} - not provided by this or a parent container"
                )

            LOGGER.debug("dependency %r not provided by this container - checking parent", dependency_id)
            return await self._parent._get(dependency_id)

        # TODO - look into caching individual dependency creation order globally
        #      - may speed up using subsequent containers (i.e. for each command)
        #      - would need to consider how to handle invalidating the cache
        subgraph = self._graph.subgraph(nx.descendants(self._graph, dependency_id) | {dependency_id})
        assert isinstance(subgraph, nx.DiGraph)

        try:
            creation_order = list(reversed(list(nx.topological_sort(subgraph))))
        except nx.NetworkXUnfeasible:
            raise exceptions.CircularDependencyException(
                f"cannot provide {dependency_id!r} - circular dependency found during creation"
            )

        LOGGER.debug("dependency %r depends on %s", dependency_id, creation_order[:-1])
        for dep_id in creation_order:
            # We already have the dependency we need
            if dep_id in self._instances:
                continue

            node_data = self._graph.nodes[dep_id]
            if node_data.get("factory") is None:
                if self._parent is None:
                    raise exceptions.DependencyNotSatisfiableException(
                        f"could not create dependency {dep_id!r} - do not know how to instantiate"
                    )
                # Ensure that the dependency is available from the parent container
                await self._parent._get(dep_id)
                continue

            sub_dependencies: dict[str, t.Any] = {}
            try:
                LOGGER.debug("checking sub-dependencies for %r", dep_id)
                for sub_dependency_id, param_name in node_data["factory_params"].items():
                    sub_dependencies[param_name] = await self._get(sub_dependency_id)
            except exceptions.DependencyNotSatisfiableException as e:
                raise exceptions.DependencyNotSatisfiableException(
                    f"could not create dependency {dep_id!r} - failed creating sub-dependency"
                ) from e

            # Cache the created dependency in the correct container to ensure the correct lifecycle
            try:
                self._instances[dep_id] = await utils.maybe_await(node_data["factory"](**sub_dependencies))
            except Exception as e:
                raise exceptions.DependencyNotSatisfiableException(
                    f"could not create dependency {dep_id!r} - factory raised exception"
                ) from e
            LOGGER.debug("instantiated dependency %r", dep_id)

        return self._instances[dependency_id]

    @t.overload
    async def get(self, type_: type[T], /) -> T: ...
    # TODO - TypeExpr
    @t.overload
    async def get(self, type_: t.Any, /) -> t.Any: ...
    async def get(self, type_: t.Any, /) -> t.Any:
        """
        Get a dependency from this container, instantiating it and sub-dependencies if necessary.

        Args:
            type_: The type used when registering the dependency.

        Returns:
            The dependency for the given type.

        Raises:
            :obj:`~lightbulb.di.exceptions.ContainerClosedException`: If the container is closed.
            :obj:`~lightbulb.di.exceptions.CircularDependencyException`: If the dependency cannot be satisfied
                due to a circular dependency with itself or a sub-dependency.
            :obj:`~lightbulb.di.exceptions.DependencyNotSatisfiableException`: If the dependency cannot be satisfied
                for any other reason.
        """
        if self._closed:
            raise exceptions.ContainerClosedException("the container is closed")

        expr = DependencyExpression.create(type_)
        return await expr.resolve(self)
