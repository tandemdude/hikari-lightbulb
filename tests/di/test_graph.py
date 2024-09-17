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
import pytest

from lightbulb.di import graph


class TestGraph:
    @pytest.fixture
    def g(self) -> graph.DiGraph:
        return graph.DiGraph()

    def test__contains__(self, g: graph.DiGraph) -> None:
        assert "foo" not in g
        g.add_node("foo", None)
        assert "foo" in g

    def test_add_remove_node(self, g: graph.DiGraph) -> None:
        g.add_node("foo", None)
        assert g.nodes["foo"] is None

        g.add_node("bar", None)
        g.add_edge("bar", "foo")

        g.remove_node("foo")
        assert "foo" not in g.nodes
        assert ("bar", "foo") not in g.edges

    def test_add_remove_edge(self, g: graph.DiGraph) -> None:
        assert not g.out_edges("foo")

        g.add_node("foo", None)
        g.add_node("bar", None)
        g.add_edge("foo", "bar")

        assert g.edges == {("foo", "bar")}

        assert not g.in_edges("foo")
        assert g.out_edges("foo") == {("foo", "bar")}

        assert not g.out_edges("bar")
        assert g.in_edges("bar") == {("foo", "bar")}

        g.remove_edge("foo", "bar")
        assert not g.out_edges("foo")

        with pytest.raises(ValueError):
            g.add_edge("foo", "baz")
        with pytest.raises(ValueError):
            g.add_edge("baz", "foo")

        g.remove_edge("baz", "bork")

    def test_children_simple(self, g: graph.DiGraph) -> None:
        g.add_node("foo", None)
        g.add_node("bar", None)
        g.add_node("baz", None)

        g.add_edge("foo", "bar")
        g.add_edge("bar", "baz")

        assert g.children("foo") == {"bar", "baz"}

    def test_children_complex(self, g: graph.DiGraph) -> None:
        g.add_node("A", None)
        g.add_node("B", None)
        g.add_node("C", None)
        g.add_node("D", None)
        g.add_node("E", None)
        g.add_node("F", None)
        g.add_node("G", None)

        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        g.add_edge("C", "E")
        g.add_edge("D", "F")
        g.add_edge("E", "F")
        g.add_edge("F", "G")

        assert g.children("A") == {"B", "C", "D", "E", "F", "G"}
        assert g.children("B") == {"D", "F", "G"}
        assert g.children("C") == {"D", "E", "F", "G"}
        assert g.children("D") == {"F", "G"}
        assert g.children("E") == {"F", "G"}
        assert g.children("F") == {"G"}
        assert g.children("G") == set()

    def test_children_circular_reference(self, g: graph.DiGraph) -> None:
        g.add_node("foo", None)
        g.add_node("bar", None)
        g.add_node("baz", None)

        g.add_edge("foo", "bar")
        g.add_edge("bar", "baz")
        g.add_edge("baz", "foo")

        assert g.children("foo") == {"bar", "baz", "foo"}

    def test_subgraph(self, g: graph.DiGraph) -> None:
        g.add_node("foo", None)
        g.add_node("bar", None)
        g.add_node("baz", None)

        g.add_edge("foo", "bar")
        g.add_edge("bar", "baz")
        g.add_edge("baz", "foo")

        sg = g.subgraph({"foo", "baz"})
        assert sg.nodes["foo"] is None
        assert sg.nodes["baz"] is None

        assert sg.edges == {("baz", "foo")}
