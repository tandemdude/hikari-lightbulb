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
    from lightbulb.internal import types

T = t.TypeVar("T")


class Registry:
    __slots__ = ("_graph",)

    def __init__(self) -> None:
        self._graph: nx.DiGraph[str] = nx.DiGraph()

    def register_value(
        self, typ: type[T], value: T, teardown: t.Callable[..., types.MaybeAwaitable[None]] | None = None
    ) -> None:
        self.register_factory(typ, lambda: value, teardown)

    def register_factory(
        self,
        typ: type[T] | t.Annotated[T, str],
        factory: t.Callable[..., types.MaybeAwaitable[T]],
        teardown: t.Callable[[T], types.MaybeAwaitable[None]] | None = None,
    ) -> None:
        dependency_id = di_utils.get_dependency_id(typ)

        # We are overriding a previously defined dependency and want to strip the edges, so we don't have
        # a load of redundant ones - maybe the new version doesn't require the same sub-dependencies
        if dependency_id in self._graph:
            self._graph.remove_edges_from(list(self._graph.out_edges(dependency_id)))

        factory_dependencies = di_utils.resolve_dependency_id_for_all_parameters(factory)

        if dependency_id in factory_dependencies:
            raise exceptions.CircularDependencyException(f"factory for type {typ!r} requires itself as a dependency")

        di_utils.populate_graph_for_dependency(self._graph, dependency_id, factory, teardown)
