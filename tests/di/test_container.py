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
import inspect
import typing as t
from unittest import mock

import pytest

from lightbulb import di
from lightbulb.di import utils

A = t.NewType("A", object)
B = t.NewType("B", object)
C = t.NewType("C", object)
D = t.NewType("D", object)
E = t.NewType("E", object)
F = t.NewType("F", object)
G = t.NewType("G", object)


class TestStandaloneContainer:
    def test_cannot_have_factory_with_pos_only_args(self) -> None:
        registry = di.Registry()

        def f(_: str, /) -> object:
            return object()

        with pytest.raises(ValueError):
            registry.register_factory(object, f)

    def test_cannot_have_factory_with_var_pos_args(self) -> None:
        registry = di.Registry()

        def f(*_: str) -> object:
            return object()

        with pytest.raises(ValueError):
            registry.register_factory(object, f)

    def test_cannot_have_factory_with_var_kw_args(self) -> None:
        registry = di.Registry()

        def f(**_: str) -> object:
            return object()

        with pytest.raises(ValueError):
            registry.register_factory(object, f)

    @pytest.mark.asyncio
    async def test_supply_dependency_by_value(self) -> None:
        value = object()

        registry = di.Registry()
        registry.register_value(object, value)

        async with di.Container(registry) as container:
            assert (await container.get(object)) is value

    @pytest.mark.asyncio
    async def test_supply_dependency_by_sync_factory(self) -> None:
        value = object()

        registry = di.Registry()
        registry.register_factory(object, lambda: value)

        async with di.Container(registry) as container:
            assert (await container.get(object)) is value

    @pytest.mark.asyncio
    async def test_supply_dependency_by_async_factory(self) -> None:
        value = object()

        async def factory() -> object:
            return value

        registry = di.Registry()
        registry.register_factory(object, factory)

        async with di.Container(registry) as container:
            assert (await container.get(object)) is value

    @pytest.mark.asyncio
    async def test_supplied_dependency_is_singleton(self) -> None:
        def side_effect() -> object:
            return object()

        factory = mock.Mock(side_effect=side_effect)
        factory.__signature__ = inspect.signature(side_effect)

        registry = di.Registry()
        registry.register_factory(object, factory)

        async with di.Container(registry) as container:
            value = await container.get(object)
            assert (await container.get(object)) is value

        factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_teardown_not_called_if_dependency_never_supplied(self) -> None:
        teardown = mock.Mock()

        registry = di.Registry()
        registry.register_factory(object, lambda: object(), teardown=teardown)

        async with di.Container(registry):
            pass

        teardown.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_teardown_called_when_dependency_supplied(self) -> None:
        teardown = mock.Mock()

        registry = di.Registry()
        registry.register_factory(object, lambda: object(), teardown=teardown)

        async with di.Container(registry) as container:
            value = await container.get(object)

        teardown.assert_called_once_with(value)

    @pytest.mark.asyncio
    async def test_async_teardown_called_when_dependency_supplied(self) -> None:
        teardown = mock.AsyncMock()

        registry = di.Registry()
        registry.register_factory(object, lambda: object(), teardown=teardown)

        async with di.Container(registry) as container:
            value = await container.get(object)

        teardown.assert_awaited_once_with(value)

    @pytest.mark.asyncio
    async def test_dependency_with_dependency_supplied(self) -> None:
        # fmt: off
        def f1() -> object: return object()
        def f2(_: A) -> object: return object()
        # fmt: on

        registry = di.Registry()
        registry.register_factory(A, f1)
        registry.register_factory(B, f2)

        async with di.Container(registry) as container:
            await container.get(B)

    @pytest.mark.asyncio
    async def test_dependency_with_multiple_dependencies_supplied(self) -> None:
        # fmt: off
        def f1() -> object: return object()
        def f2() -> object: return object()
        def f3(_: A, __: B) -> object: return object()
        # fmt: on

        registry = di.Registry()
        registry.register_factory(A, f1)
        registry.register_factory(B, f2)
        registry.register_factory(C, f3)

        async with di.Container(registry) as container:
            await container.get(C)

    @pytest.fixture
    def complicated_registry(self) -> di.Registry:
        # fmt: off
        def f_a() -> object: return object()
        def f_b(_: A) -> object: return object()
        def f_c(_: A) -> object: return object()
        def f_d(_: B) -> object: return object()
        def f_e(_: B, __: C) -> object: return object()
        def f_f(_: A, __: E) -> object: return object()
        def f_g(_: A, __: D, ___: F) -> object: return object()
        # fmt: on

        registry = di.Registry()
        registry.register_factory(A, f_a, teardown=mock.Mock())
        registry.register_factory(B, f_b, teardown=mock.Mock())
        registry.register_factory(C, f_c, teardown=mock.Mock())
        registry.register_factory(D, f_d, teardown=mock.Mock())
        registry.register_factory(E, f_e, teardown=mock.Mock())
        registry.register_factory(F, f_f, teardown=mock.Mock())
        registry.register_factory(G, f_g, teardown=mock.Mock())

        return registry

    @pytest.mark.asyncio
    async def test_complicated_dependency_supplied(self, complicated_registry: di.Registry) -> None:
        async with di.Container(complicated_registry) as container:
            await container.get(G)

    @pytest.mark.asyncio
    async def test_all_teardowns_called_for_complicated_dependency(self, complicated_registry: di.Registry) -> None:
        async with di.Container(complicated_registry) as container:
            await container.get(G)

        for item in [A, B, C, D, E, F, G]:
            complicated_registry._graph.nodes[utils.get_dependency_id(item)]["teardown"].assert_called_once()

    @pytest.mark.asyncio
    async def test_direct_unsatisfied_dependency_raises_exception(self) -> None:
        registry = di.Registry()

        with pytest.raises(di.DependencyNotSatisfiableException):
            async with di.Container(registry) as container:
                await container.get(object)

    @pytest.mark.asyncio
    async def test_indirect_unsatisfied_dependency_raises_exception(self) -> None:
        def f(_: A) -> object:
            return object()

        registry = di.Registry()
        registry.register_factory(B, f)

        with pytest.raises(di.DependencyNotSatisfiableException):
            async with di.Container(registry) as container:
                await container.get(B)


class TestContainerWithParent:
    @pytest.mark.asyncio
    async def test_dependency_from_parent_supplied(self) -> None:
        parent_registry = di.Registry()
        parent_registry.register_factory(object, lambda: object())

        child_registry = di.Registry()

        async with (
            di.Container(parent_registry) as pc,
            di.Container(child_registry, parent=pc) as cc,
        ):
            await cc.get(object)

    @pytest.mark.asyncio
    async def test_dependency_from_parent_ignores_child_lifecycle(self) -> None:
        parent_registry = di.Registry()
        parent_registry.register_factory(object, lambda: object())

        child_registry = di.Registry()

        async with di.Container(parent_registry) as pc:
            async with di.Container(child_registry, parent=pc) as cc1:
                dep = await cc1.get(object)

            async with di.Container(child_registry, parent=pc) as cc2:
                assert (await cc2.get(object)) is dep

    @pytest.mark.asyncio
    async def test_overridden_dependency_used_instead_of_parent(self) -> None:
        parent_registry = di.Registry()
        parent_registry.register_factory(object, lambda: object())

        child_registry = di.Registry()

        async with di.Container(parent_registry) as pc:
            async with di.Container(child_registry, parent=pc) as cc1:
                parent_dep = await cc1.get(object)

            child_registry.register_value(object, object())

            async with di.Container(child_registry, parent=pc) as cc2:
                assert (await cc2.get(object)) is not parent_dep

            assert (await pc.get(object)) is parent_dep

    @pytest.mark.asyncio
    async def test_parent_dependency_cannot_depend_on_child_dependency(self) -> None:
        def f(_: A) -> object:
            return object()

        parent_registry = di.Registry()
        parent_registry.register_factory(B, f)

        child_registry = di.Registry()
        child_registry.register_factory(A, lambda: object())

        with pytest.raises(di.DependencyNotSatisfiableException):
            async with (
                di.Container(parent_registry) as pc,
                di.Container(child_registry, parent=pc) as cc,
            ):
                await cc.get(B)

    @pytest.mark.asyncio
    async def test_non_direct_circular_dependency_raises_exception(self) -> None:
        # fmt: off
        def f_a(_: B) -> object: return object()
        def f_b(_: A) -> object: return object()
        # fmt: on

        registry = di.Registry()
        registry.register_factory(A, f_a)
        registry.register_factory(B, f_b)

        with pytest.raises(di.CircularDependencyException):
            async with di.Container(registry) as c:
                await c.get(A)

    @pytest.mark.asyncio
    async def test_get_transient_dependency_raises_exception(self) -> None:
        def f_a(_: B) -> object:
            return object()

        registry = di.Registry()
        registry.register_factory(A, f_a)

        with pytest.raises(di.DependencyNotSatisfiableException):
            async with di.Container(registry) as c:
                await c.get(B)

    @pytest.mark.asyncio
    async def test_get_from_closed_container_raises_exception(self) -> None:
        registry = di.Registry()
        registry.register_factory(object, lambda: object())

        with pytest.raises(di.ContainerClosedException):
            async with di.Container(registry) as c:
                pass
            await c.get(object)
