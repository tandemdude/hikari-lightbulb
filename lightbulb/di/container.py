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

__all__ = ["Container"]

import typing as t

import networkx as nx

from lightbulb import utils
from lightbulb.di import exceptions
from lightbulb.di import registry as registry_
from lightbulb.di import utils as di_utils

if t.TYPE_CHECKING:
    import types

    from lightbulb.internal import types as lb_types

T = t.TypeVar("T")


class Container:
    """
    A container for managing and supplying dependencies.

    Args:
        registry: The registry of dependencies supply-able by this container.
        parent: The parent container. Defaults to None.
    """

    __slots__ = ("_registry", "_parent", "_closed", "_graph", "_instances")

    def __init__(self, registry: registry_.Registry, *, parent: Container | None = None) -> None:
        self._registry = registry
        self._registry._freeze(self)
        self._parent = parent

        self._closed = False

        self._graph: nx.DiGraph[str] = nx.DiGraph(self._parent._graph) if self._parent is not None else nx.DiGraph()
        self._instances: dict[str, t.Any] = {}

        # Add our registry entries to the graphs
        for node, node_data in self._registry._graph.nodes.items():
            new_node_data = dict(node_data)

            # Set the origin container if this is a concrete dependency instead of a transient one
            if node_data.get("factory") is not None:
                new_node_data["container"] = self

            # If we are overriding a previously defined dependency with our own
            if node in self._graph and node_data.get("factory") is not None:
                self._graph.remove_edges_from(list(self._graph.out_edges(node)))

            self._graph.add_node(node, **new_node_data)
        self._graph.add_edges_from(self._registry._graph.edges)

        self.add_value(Container, self)

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
        factory: t.Callable[..., lb_types.MaybeAwaitable[T]],
        *,
        teardown: t.Callable[[T], lb_types.MaybeAwaitable[None]] | None = None,
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
            :meth:`lightbulb.di.registry.Registry.add_factory` for factory and teardown function spec.
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
        teardown: t.Callable[[T], lb_types.MaybeAwaitable[None]] | None = None,
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
            :meth:`lightbulb.di.registry.Registry.add_value` for teardown function spec.
        """
        dependency_id = di_utils.get_dependency_id(typ)
        self._instances[dependency_id] = value

        if dependency_id in self._graph:
            self._graph.remove_edges_from(list(self._graph.out_edges(dependency_id)))
        self._graph.add_node(dependency_id, container=self, teardown=teardown)

    async def _get(self, dependency_id: str) -> t.Any:
        if self._closed:
            raise exceptions.ContainerClosedException

        # TODO - look into whether locking is necessary - how likely are we to have race conditions

        data = self._graph.nodes.get(dependency_id)
        if data is None or data.get("container") is None:
            raise exceptions.DependencyNotSatisfiableException

        existing_dependency = data["container"]._instances.get(dependency_id)
        if existing_dependency is not None:
            return existing_dependency

        # TODO - look into caching individual dependency creation order globally
        #      - may speed up using subsequent containers (i.e. for each command)
        #      - would need to consider how to handle invalidating the cache
        subgraph = self._graph.subgraph(nx.descendants(self._graph, dependency_id) | {dependency_id})
        assert isinstance(subgraph, nx.DiGraph)

        try:
            creation_order = reversed(list(nx.topological_sort(subgraph)))
        except nx.NetworkXUnfeasible:
            raise exceptions.CircularDependencyException(
                f"cannot provide {dependency_id!r} - circular dependency found during creation"
            )

        for dep_id in creation_order:
            if (container := self._graph.nodes[dep_id].get("container")) is None:
                raise exceptions.DependencyNotSatisfiableException(
                    f"could not create dependency {dep_id!r} - not provided by this or a parent container"
                )

            # We already have the dependency we need
            if dep_id in container._instances:
                continue

            node_data = self._graph.nodes[dep_id]
            # Check that we actually know how to create the dependency - this should have been caught earlier
            # by checking that node["container"] was present - but just in case, we check for the factory
            if node_data.get("factory") is None:
                raise exceptions.DependencyNotSatisfiableException(
                    f"could not create dependency {dep_id!r} - do not know how to instantiate"
                )

            # Get the dependencies for this dependency from the container this dependency was defined in.
            # This prevents 'scope promotion' - a dependency from the parent container requiring one from the
            # child container, and hence the lifecycle of the child dependency being extended to
            # that of the parent.
            sub_dependencies: dict[str, t.Any] = {}
            try:
                for sub_dependency_id, param_name in node_data["factory_params"].items():
                    sub_dependencies[param_name] = await node_data["container"]._get(sub_dependency_id)
            except exceptions.DependencyNotSatisfiableException as e:
                raise exceptions.DependencyNotSatisfiableException(
                    f"could not create dependency {dep_id!r} - failed creating sub-dependency"
                ) from e

            # Cache the created dependency in the correct container to ensure the correct lifecycle
            container._instances[dep_id] = await utils.maybe_await(node_data["factory"](**sub_dependencies))

        return self._graph.nodes[dependency_id]["container"]._instances[dependency_id]

    async def get(self, typ: type[T]) -> T:
        """
        Get a dependency from this container, instantiating it and sub-dependencies if necessary.

        Args:
            typ: The type used when registering the dependency.

        Returns:
            The dependency for the given type.

        Raises:
            :obj:`~lightbulb.di.exceptions.ContainerClosedException`: If the container is closed.
            :obj:`~lightbulb.di.exceptions.CircularDependencyException`: If the dependency cannot be satisfied
                due to a circular dependency with itself or a sub-dependency.
            :obj:`~lightbulb.di.exceptions.DependencyNotSatisfiableException`: If the dependency cannot be satisfied
                for any other reason.
        """
        dependency_id = di_utils.get_dependency_id(typ)
        return t.cast(T, await self._get(dependency_id))
