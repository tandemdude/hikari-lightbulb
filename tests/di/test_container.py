import inspect
import typing as t
from unittest import mock

import pytest

from lightbulb import di


class TestStandaloneContainer:
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
        registry.register_factory(object, lambda: object(), teardown)

        async with di.Container(registry):
            pass

        teardown.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.xfail
    async def test_sync_teardown_called_when_dependency_supplied(self) -> None:
        teardown = mock.Mock()

        registry = di.Registry()
        registry.register_factory(object, lambda: object(), teardown)

        async with di.Container(registry) as container:
            value = await container.get(object)

        teardown.assert_called_once_with(value)

    @pytest.mark.asyncio
    @pytest.mark.xfail
    async def test_async_teardown_called_when_dependency_supplied(self) -> None:
        teardown = mock.AsyncMock()

        registry = di.Registry()
        registry.register_factory(object, lambda: object(), teardown)

        async with di.Container(registry) as container:
            value = await container.get(object)

        teardown.assert_awaited_once_with(value)

    @pytest.mark.asyncio
    async def test_dependency_with_dependency_supplied(self) -> None:
        # fmt: off
        def f1() -> object: return object()
        def f2(_: t.Annotated[object, "d1"]) -> object: return object()
        # fmt: on

        d1 = t.Annotated[object, "d1"]
        d2 = t.Annotated[object, "d2"]

        registry = di.Registry()
        registry.register_factory(d1, f1)
        registry.register_factory(d2, f2)

        async with di.Container(registry) as container:
            await container.get(d2)

    @pytest.mark.asyncio
    async def test_dependency_with_multiple_dependencies_supplied(self) -> None:
        # fmt: off
        def f1() -> object: return object()
        def f2() -> object: return object()
        def f3(_: t.Annotated[object, "d1"], __: t.Annotated[object, "d2"]) -> object: return object()
        # fmt: on

        d1 = t.Annotated[object, "d1"]
        d2 = t.Annotated[object, "d2"]
        d3 = t.Annotated[object, "d3"]

        registry = di.Registry()
        registry.register_factory(d1, f1)
        registry.register_factory(d2, f2)
        registry.register_factory(d3, f3)

        async with di.Container(registry) as container:
            await container.get(d3)

    @pytest.fixture
    def complicated_registry(self) -> di.Registry:
        # fmt: off
        def f_a() -> object: return object()
        def f_b(_: t.Annotated[object, "a"]) -> object: return object()
        def f_c(_: t.Annotated[object, "a"]) -> object: return object()
        def f_d(_: t.Annotated[object, "b"]) -> object: return object()
        def f_e(_: t.Annotated[object, "b"], __: t.Annotated[object, "c"]) -> object: return object()
        def f_f(_: t.Annotated[object, "a"], __: t.Annotated[object, "e"]) -> object: return object()
        def f_g(_: t.Annotated[object, "a"], __: t.Annotated[object, "d"], ___: t.Annotated[object, "f"]) -> object: return object()  # noqa: E501
        # fmt: on

        registry = di.Registry()
        registry.register_factory(t.Annotated[object, "a"], f_a, mock.Mock())
        registry.register_factory(t.Annotated[object, "b"], f_b, mock.Mock())
        registry.register_factory(t.Annotated[object, "c"], f_c, mock.Mock())
        registry.register_factory(t.Annotated[object, "d"], f_d, mock.Mock())
        registry.register_factory(t.Annotated[object, "e"], f_e, mock.Mock())
        registry.register_factory(t.Annotated[object, "f"], f_f, mock.Mock())
        registry.register_factory(t.Annotated[object, "g"], f_g, mock.Mock())

        return registry

    @pytest.mark.asyncio
    async def test_complicated_dependency_supplied(self, complicated_registry: di.Registry) -> None:
        async with di.Container(complicated_registry) as container:
            await container.get(t.Annotated[object, "g"])

    @pytest.mark.asyncio
    @pytest.mark.xfail
    async def test_all_teardowns_called_for_complicated_dependency(self, complicated_registry: di.Registry) -> None:
        async with di.Container(complicated_registry) as container:
            await container.get(t.Annotated[object, "g"])

        for item in ["a", "b", "c", "d", "e", "f", "g"]:
            complicated_registry._graph.nodes[item]["teardown"].assert_called_once()

    @pytest.mark.asyncio
    async def test_direct_unsatisfied_dependency_raises_exception(self) -> None:
        registry = di.Registry()

        with pytest.raises(di.DependencyNotSatisfiableException):
            async with di.Container(registry) as container:
                await container.get(object)

    @pytest.mark.asyncio
    async def test_indirect_unsatisfied_dependency_raises_exception(self) -> None:
        def f(_: t.Annotated[object, "d1"]) -> object:
            return object()

        registry = di.Registry()
        registry.register_factory(t.Annotated[object, "d2"], f)

        with pytest.raises(di.DependencyNotSatisfiableException):
            async with di.Container(registry) as container:
                await container.get(t.Annotated[object, "d2"])


class TestContainerWithParent:
    @pytest.mark.asyncio
    async def test_dependency_from_parent_supplied(self) -> None:
        parent_registry = di.Registry()
        parent_registry.register_factory(object, lambda: object())

        child_registry = di.Registry()

        async with di.Container(parent_registry) as pc, di.Container(child_registry, parent=pc) as cc:
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
        def f(_: t.Annotated[object, "d1"]) -> object:
            return object()

        parent_registry = di.Registry()
        parent_registry.register_factory(t.Annotated[object, "d2"], f)

        child_registry = di.Registry()
        child_registry.register_factory(t.Annotated[object, "d1"], lambda: object())

        with pytest.raises(di.DependencyNotSatisfiableException):
            async with di.Container(parent_registry) as pc, di.Container(child_registry, parent=pc) as cc:
                await cc.get(t.Annotated[object, "d2"])
