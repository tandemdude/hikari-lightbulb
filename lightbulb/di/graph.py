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

__all__ = ["DependencyData", "DiGraph"]

import collections
import inspect
import sys
import typing as t

from lightbulb.di import conditions
from lightbulb.di import exceptions

if t.TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Mapping
    from collections.abc import Set

    from lightbulb.internal import types

T = t.TypeVar("T")


class DependencyData(t.Generic[T]):
    """
    Data required in order to be able to create/destroy a given dependency.

    Args:
        factory_method: The method used to create the dependency.
        factory_params: Mapping of param name to dependency expression for any dependencies the factory depends on.
        teardown_method: The optional method used to teardown the dependency.
    """

    __slots__ = ("factory_method", "factory_params", "teardown_method")

    def __init__(
        self,
        factory_method: Callable[..., types.MaybeAwaitable[T]],
        factory_params: Mapping[str, conditions.DependencyExpression[T]],
        teardown_method: Callable[[T], types.MaybeAwaitable[None]] | None,
    ) -> None:
        self.factory_method: Callable[..., types.MaybeAwaitable[T]] = factory_method
        """The method used to create the dependency."""
        self.factory_params: Mapping[str, conditions.DependencyExpression[T]] = factory_params
        """Mapping of param name to dependency expression for any dependencies the factory depends on."""
        self.teardown_method: Callable[[T], types.MaybeAwaitable[None]] | None = teardown_method
        """The optional method used to teardown the dependency."""


def resolve_dependency_expression_for_all_parameters(
    func: Callable[..., types.MaybeAwaitable[t.Any]],
) -> dict[str, conditions.DependencyExpression[t.Any]]:
    """
    Parse all parameters of the given callable and find the dependency ID that should be used when
    injecting values into each parameter.

    Args:
        func: The callable to resolve dependencies for.

    Returns:
        Dictionary mapping dependency ID to the name of the parameter they should be injected into.

    Raises:
        :obj:`ValueError`: If any of the parameters are positional only, var positional, or var keyword.
    """
    dependencies: dict[str, conditions.DependencyExpression[t.Any]] = {}

    for param in inspect.signature(
        func, locals={"lightbulb": sys.modules["lightbulb"]}, eval_str=True
    ).parameters.values():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise ValueError("functions cannot have positional only, var-positional, or var-keyword arguments")

        if param.annotation is inspect.Parameter.empty:
            raise ValueError("all parameters must have a type annotation")

        dependencies[param.name] = conditions.DependencyExpression.create(param.annotation)

    return dependencies


def populate_graph_for_dependency(
    graph: DiGraph,
    dependency_id: str,
    factory: Callable[..., types.MaybeAwaitable[t.Any]],
    teardown: Callable[..., types.MaybeAwaitable[None]] | None,
) -> None:
    """
    Populate the given dependency graph with the given dependency ID, using the factory to resolve any dependencies
    required by this dependency. You should probably never have to call this function - Lightbulb only uses it
    internally.

    Args:
        graph: The graph to add the dependency to.
        dependency_id: The ID of the dependency to add.
        factory: The factory to use to create the dependency.
        teardown: The teardown function to use to destroy the dependency.

    Returns:
        :obj:`None`
    """
    factory_dependencies = resolve_dependency_expression_for_all_parameters(factory)
    dependency_data = DependencyData(factory, factory_dependencies, teardown)

    graph.replace_node(dependency_id, dependency_data)
    for expr in factory_dependencies.values():
        for item in expr._order:
            if item.inner_id == dependency_id:
                raise exceptions.CircularDependencyException(
                    f"factory for {dependency_id!r} requires itself as a dependency"
                )

            graph.add_node(item.inner_id, None)
            graph.add_edge(dependency_id, item.inner_id)


class DiGraph:
    """
    Implementation of a directional graph datastructure for use as a dependency graph.

    Args:
        initial: The initial graph to use to populate the starting state of the graph. Defaults to ``None``.
    """

    __slots__ = ("_adjacency", "_nodes")

    def __init__(self, initial: DiGraph | None = None) -> None:
        self._nodes: dict[str, DependencyData[t.Any] | None] = {}
        self._adjacency: dict[str, set[str]] = collections.defaultdict(set)

        if initial is not None:
            self._nodes.update(initial._nodes)
            for id_, adj in initial._adjacency.items():
                self._adjacency[id_].update(adj)

    def __contains__(self, item: str) -> bool:
        return item in self._nodes

    @property
    def nodes(self) -> Mapping[str, DependencyData[t.Any] | None]:
        """
        Mapping of dependency ID to the data for that dependency. If the data is ``None``, it indicates
        that the node was added indirectly and that the dependency for that ID has not been directly
        registered to this graph.
        """
        return self._nodes

    @property
    def edges(self) -> Set[tuple[str, str]]:
        """
        Set containing all edges within this graph. An edge is represented by a tuple where the first element
        is the origin node, and the second element is the destination node.
        """
        all_edges: set[tuple[str, str]] = set()
        for node, edges in self._adjacency.items():
            all_edges.update((node, other) for other in edges)

        return all_edges

    def out_edges(self, id_: str, /) -> Set[tuple[str, str]]:
        """
        Get the out edges for the node with the given dependency ID. In the context of DI, the edges
        represent the dependencies that the requested dependency directly depends on.

        Args:
            id_: The ID of the dependency to get out edges for.

        Returns:
            The out edges for the node with the given dependency ID.
        """
        return {(id_, other) for other in self._adjacency[id_]}

    def in_edges(self, id_: str, /) -> Set[tuple[str, str]]:
        """
        Get the in edges for the node with the given dependency ID. In the context of DI, the edges
        represent the dependencies that depend on the requested dependency.

        Args:
            id_: The ID of the dependency to get in edges for.

        Returns:
            The in edges for the node with the given dependency ID.
        """
        return {(node, id_) for node, edges in self._adjacency.items() if id_ in edges}

    def add_node(self, id_: str, /, data: DependencyData[t.Any] | None) -> None:
        """
        Add a node to the graph.

        Args:
            id_: The ID of the node to add.
            data: The data for the node.

        Returns:
            :obj:`None`
        """
        if id_ in self._nodes:
            return

        self._nodes[id_] = data

    def remove_node(self, id_: str, /) -> None:
        """
        Remove a node from the graph. Does nothing if the node is not present in the graph. Also
        removes all edges referencing the node.

        Args:
            id_: The ID of the node to remove.

        Returns:
            :obj:`None`
        """
        self._nodes.pop(id_, None)
        self._adjacency.pop(id_, None)

        for adj in self._adjacency.values():
            adj.discard(id_)

    def replace_node(self, id_: str, /, data: DependencyData[t.Any] | None) -> None:
        """
        Replace the data for the node with the given ID. Preserves all edges already referencing this
        node. Adds the node if it is not already in the graph.

        Args:
            id_: The ID of the node to replace.
            data: The data for the node.

        Returns:
            :obj:`None`
        """
        self._nodes[id_] = data

    def add_edge(self, from_: str, to_: str, /) -> None:
        """
        Add an edge to the graph. Fails if either the origin or destination nodes are not in the graph.

        Args:
            from_: The origin node.
            to_: The destination node.

        Returns:
            :obj:`None`

        Raises:
            :obj:`ValueError`: If either the origin or destination nodes are not in the graph.
        """
        if from_ not in self._nodes:
            raise ValueError(f"node {from_!r} is not in the graph")
        if to_ not in self._nodes:
            raise ValueError(f"node {to_!r} is not in the graph")

        self._adjacency[from_].add(to_)

    def remove_edge(self, from_: str, to_: str, /) -> None:
        """
        Remove an edge from the graph. Does nothing if either the origin or destination nodes are not in the graph.

        Args:
            from_: The origin node.
            to_: The destination node.

        Returns:
            :obj:`None`
        """
        if from_ not in self._nodes or to_ not in self._nodes:
            return

        self._adjacency[from_].discard(to_)

    def children(self, of: str, /) -> Set[str]:
        """
        Get the set of all children for the given node. Includes indirect children where a node depends on a
        node that depends on the requested node (etc.).

        Args:
            of: The node to get the children for.

        Returns:
            Set of all children for the given node.
        """
        children_: set[str] = set()

        to_process, index = list(self._adjacency[of]), 0
        while index < len(to_process):
            if (current := to_process[index]) not in children_:
                children_.add(current)
                to_process.extend(self._adjacency[current])

            index += 1

        return children_

    def subgraph(self, of: Collection[str], /) -> DiGraph:
        """
        Create a subgraph containing only the given nodes, and any edges relating them. The created
        graph will **only** contain the requested nodes, and no nodes that depend on any of the given nodes
        that were not specified.

        Args:
            of: The nodes the subgraph should contain.

        Returns:
            The created subgraph.
        """
        subgraph: DiGraph = DiGraph()

        nodes = set(n for n in of if n in self._nodes)
        for node in nodes:
            subgraph.add_node(node, self._nodes[node])
            subgraph._adjacency[node] = nodes & self._adjacency[node]

        return subgraph
