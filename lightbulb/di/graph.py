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

__all__ = ["DiGraph"]

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
    __slots__ = ("factory_method", "factory_params", "teardown_method")

    def __init__(
        self,
        factory_method: Callable[..., types.MaybeAwaitable[T]],
        factory_params: Mapping[str, conditions.DependencyExpression[T]],
        teardown_method: Callable[[T], types.MaybeAwaitable[None]] | None,
    ) -> None:
        self.factory_method: Callable[..., types.MaybeAwaitable[T]] = factory_method
        self.factory_params: Mapping[str, conditions.DependencyExpression[T]] = factory_params
        self.teardown_method: Callable[[T], types.MaybeAwaitable[None]] | None = teardown_method


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
        return self._nodes

    def out_edges(self, id_: str, /) -> Set[str]:
        return self._adjacency[id_]

    def add_node(self, id_: str, /, data: DependencyData[t.Any] | None) -> None:
        if id_ in self._nodes:
            return

        self._nodes[id_] = data

    def remove_node(self, id_: str, /) -> None:
        self._nodes.pop(id_, None)
        self._adjacency.pop(id_, None)

        for adj in self._adjacency.values():
            adj.discard(id_)

    def replace_node(self, id_: str, /, data: DependencyData[t.Any]) -> None:
        self._nodes[id_] = data

    def add_edge(self, from_: str, to_: str, /) -> None:
        if from_ not in self._nodes:
            raise ValueError(f"node {from_!r} is not in the graph")
        if to_ not in self._nodes:
            raise ValueError(f"node {to_!r} is not in the graph")

        self._adjacency[from_].add(to_)

    def remove_edge(self, from_: str, to_: str, /) -> None:
        if from_ not in self._nodes or to_ not in self._nodes:
            return

        self._adjacency[from_].discard(to_)

    def children(self, of: str, /) -> Set[str]:
        children_: set[str] = set()

        to_process, index = list(self._adjacency[of]), 0
        while index < len(to_process):
            if (current := to_process[index]) not in children_:
                children_.add(current)
                to_process.extend(self._adjacency[current])

            index += 1

        return children_

    def subgraph(self, of: Collection[str], /) -> DiGraph:
        subgraph: DiGraph = DiGraph()

        nodes = set(n for n in of if n in self._nodes)
        for node in nodes:
            subgraph.add_node(node, self._nodes[node])
            subgraph._adjacency[node] = nodes & self._adjacency[node]

        return subgraph
