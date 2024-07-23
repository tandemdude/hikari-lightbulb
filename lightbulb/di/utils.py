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

__all__ = ["get_dependency_id", "resolve_dependency_id_for_all_parameters", "populate_graph_for_dependency"]

import inspect
import sys
import typing as t

if t.TYPE_CHECKING:
    import networkx as nx

    from lightbulb.internal import types


def get_dependency_id(dependency_type: type[t.Any]) -> str:
    """
    Get the dependency id of the given type. This is used when storing and retrieving dependencies from registries
    and containers.

    Args:
        dependency_type: The type to get the dependency id for.

    Returns:
        The dependency id for the given type.
    """
    return f"{dependency_type.__module__}.{getattr(dependency_type, '__qualname__', dependency_type.__name__)}"


def resolve_dependency_id_for_all_parameters(func: t.Callable[..., types.MaybeAwaitable[t.Any]]) -> dict[str, str]:
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
    dependencies: dict[str, str] = {}

    for param in inspect.signature(
        func, locals={"lightbulb": sys.modules["lightbulb"]}, eval_str=True
    ).parameters.values():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise ValueError("functions cannot have positional only, var-positional, or var-keyword arguments")

        dependency_id = (
            get_dependency_id(param.annotation) if param.annotation is not inspect.Parameter.empty else param.name
        )
        dependencies[dependency_id] = param.name

    return dependencies


def populate_graph_for_dependency(
    graph: nx.DiGraph[str],
    dependency_id: str,
    factory: t.Callable[..., types.MaybeAwaitable[t.Any]],
    teardown: t.Callable[..., types.MaybeAwaitable[None]] | None,
    **extra_data: t.Any,
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
        **extra_data: Any extra attributes to add to the dependency's record.

    Returns:
        :obj:`None`
    """
    factory_dependencies = resolve_dependency_id_for_all_parameters(factory)

    graph.add_node(dependency_id, factory=factory, factory_params=factory_dependencies, teardown=teardown, **extra_data)
    for dep_id in factory_dependencies:
        if dep_id not in graph.nodes:
            graph.add_node(dep_id)

        graph.add_edge(dependency_id, dep_id)
