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
import typing as t
from unittest import mock

import pytest

import lightbulb
from lightbulb.di import solver
from lightbulb.di.solver import CANNOT_INJECT
from lightbulb.di.solver import _parse_injectable_params


class TestSignatureParsing:
    def test_parses_positional_only_arg_correctly(self) -> None:
        def m(foo: object, /) -> None: ...

        pos, kw = _parse_injectable_params(m)
        assert pos[0][1] is CANNOT_INJECT and len(kw) == 0

    def test_parses_var_positional_arg_correctly(self) -> None:
        def m(*foo: object) -> None: ...

        pos, kw = _parse_injectable_params(m)
        assert len(pos) == 0 and len(kw) == 0

    def test_does_not_parse_var_kw_arg(self) -> None:
        def m(**foo: object) -> None: ...

        pos, kw = _parse_injectable_params(m)
        assert len(pos) == 0 and len(kw) == 0

    def test_parses_args_with_non_INJECTED_default_correctly(self) -> None:
        def m(foo: object = object()) -> None: ...

        pos, kw = _parse_injectable_params(m)
        assert pos[0][1] is CANNOT_INJECT and len(kw) == 0

    def test_parses_args_with_no_annotation_correctly(self) -> None:
        def m(foo) -> None:  # type: ignore[unknownParameterType]
            ...

        pos, kw = _parse_injectable_params(m)  # type: ignore[unknownArgumentType]
        assert pos[0][1] is CANNOT_INJECT and len(kw) == 0

    def test_parses_args_correctly(self) -> None:
        def m(
            foo: str, bar: int = lightbulb.di.INJECTED, *, baz: float, bork: bool = lightbulb.di.INJECTED
        ) -> None: ...

        pos, kw = _parse_injectable_params(m)

        assert len(pos) == 2
        assert pos[0][1]._order[0].inner is str and pos[0][1]._required
        assert pos[1][1]._order[0].inner is int and pos[1][1]._required

        assert len(kw) == 2
        assert kw["baz"]._order[0].inner is float and kw["baz"]._required
        assert kw["bork"]._order[0].inner is bool and kw["bork"]._required


class TestMethodInjection:
    @pytest.mark.asyncio
    async def test_exception_raised_when_no_context_available(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        def m(obj: object = lightbulb.di.INJECTED) -> None:
            assert obj is value

        with pytest.raises(lightbulb.di.DependencyNotSatisfiableException):
            await m()

    @pytest.mark.asyncio
    async def test_injection_by_type_synchronous(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        def m(obj: object = lightbulb.di.INJECTED) -> None:
            assert obj is value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_injection_by_type_asynchronous(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        async def m(obj: object = lightbulb.di.INJECTED) -> None:
            assert obj is value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_injection_by_new_type(self) -> None:
        Foo = t.NewType("Foo", object)

        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(Foo, value)

        @lightbulb.di.with_di
        async def m(obj: Foo = lightbulb.di.INJECTED) -> None:
            assert obj is value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_injection_keyword_only_parameter(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        async def m(*, obj: object = lightbulb.di.INJECTED) -> None:
            assert obj is value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_no_injection_when_parameter_passed(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        async def m(obj: object = lightbulb.di.INJECTED) -> None:
            assert obj is not value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m(object())

    @pytest.mark.asyncio
    async def test_no_injection_when_parameter_passed_by_keyword(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        async def m(obj: object = lightbulb.di.INJECTED) -> None:
            assert obj is not value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m(obj=object())

    @pytest.mark.asyncio
    async def test_self_correctly_provided_for_bound_method(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        instance: t.Optional["AClass"] = None

        class AClass:
            @lightbulb.di.with_di
            async def bound_method(self) -> None:
                assert self is instance

        instance = AClass()

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await instance.bound_method()

    @pytest.mark.asyncio
    async def test_dependency_provided_for_bound_method(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        class AClass:
            @lightbulb.di.with_di
            async def bound_method(self, obj: object = lightbulb.di.INJECTED) -> None:
                assert obj is value

        instance = AClass()

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await instance.bound_method()

    @pytest.mark.asyncio
    async def test_dependency_provided_when_argument_passed_for_bound_method(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        Value = t.NewType("Value", object)
        value, obj_ = Value(object()), object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(Value, value)

        class AClass:
            @lightbulb.di.with_di
            async def bound_method(self, obj: object, val: Value = lightbulb.di.INJECTED) -> None:
                assert obj is obj_
                assert val is value

        instance = AClass()

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await instance.bound_method(obj_)

    @pytest.mark.asyncio
    async def test_dependency_provided_when_argument_passed_to_non_annotated_parameter(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        def m(foo, obj: object = lightbulb.di.INJECTED) -> None:  # type: ignore[reportUnknownParameterType]
            assert obj is value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m("bar")


class TestDependencyInjectionManager:
    @pytest.mark.asyncio
    async def test_default_container_not_closed_once_default_context_exited(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            pass

        assert manager.default_container is not None
        assert not manager.default_container._closed

    @pytest.mark.asyncio
    async def test_default_container_not_closed_once_sub_context_exited(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        async with (
            manager.enter_context(lightbulb.di.Contexts.DEFAULT),
            manager.enter_context(lightbulb.di.Contexts.COMMAND),
        ):
            pass

        assert manager.default_container is not None
        assert not manager.default_container._closed

    @pytest.mark.asyncio
    async def test_default_container_closed_once_manager_closed(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        async with (
            manager.enter_context(lightbulb.di.Contexts.DEFAULT),
            manager.enter_context(lightbulb.di.Contexts.COMMAND),
        ):
            pass

        assert manager.default_container is not None
        default_container = manager.default_container

        await manager.close()
        assert default_container._closed
        assert manager.default_container is None

    @pytest.mark.asyncio
    async def test_entering_child_context_twice_returns_same_container(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        async with (
            manager.enter_context(lightbulb.di.Contexts.DEFAULT),
            manager.enter_context(lightbulb.di.Contexts.COMMAND) as c1,
            manager.enter_context(lightbulb.di.Contexts.COMMAND) as c2,
        ):
            assert c1 is c2

    @pytest.mark.asyncio
    async def test_entering_parent_context_twice_returns_same_container(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        async with (
            manager.enter_context(lightbulb.di.Contexts.DEFAULT) as c1,
            manager.enter_context(lightbulb.di.Contexts.COMMAND),
            manager.enter_context(lightbulb.di.Contexts.DEFAULT) as c2,
        ):
            assert c1 is c2

    @pytest.mark.asyncio
    async def test_entering_default_context_always_returns_same_container(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT) as c1:
            pass
        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT) as c2:
            assert c1 is c2

    @pytest.mark.asyncio
    async def test_enter_context_yields_noop_container_when_di_globally_disabled(self) -> None:
        with mock.patch.object(solver, "DI_ENABLED", False):
            manager = lightbulb.di.DependencyInjectionManager()
            async with manager.enter_context(lightbulb.di.Contexts.DEFAULT) as c1:
                assert c1 is solver._NOOP_CONTAINER

    @pytest.mark.asyncio
    async def test_noop_container_raises_exception_when_attempting_to_retrieve_dependency(self) -> None:
        with pytest.raises(lightbulb.di.DependencyNotSatisfiableException):
            await solver._NOOP_CONTAINER.get(object)

    @pytest.mark.asyncio
    async def test_noop_container_does_not_raise_exception_when_adding_dependency(self) -> None:
        solver._NOOP_CONTAINER.add_value(object, object())
        solver._NOOP_CONTAINER.add_factory(object, object)


class TestAutoInjecting:
    def test_setattr_passes_through_to_wrapped_function(self) -> None:
        wrapped = lightbulb.di.with_di(func := lambda: "foo")
        setattr(wrapped, "__lb_test__", "bar")
        assert getattr(func, "__lb_test__") == "bar"

    def test_getattr_passes_through_to_wrapped_function(self) -> None:
        wrapped = lightbulb.di.with_di(func := lambda: "foo")
        setattr(func, "__lb_test__", "bar")
        assert getattr(wrapped, "__lb_test__") == "bar"

    def test__get__does_not_bind_when_called_on_class(self) -> None:
        class Foo:
            @lightbulb.di.with_di
            def bar(self) -> None: ...

        assert Foo.bar._self is None  # type: ignore[reportFunctionMemberAccess]

    def test__get__binds_when_called_on_instance(self) -> None:
        class Foo:
            @lightbulb.di.with_di
            def bar(self) -> None: ...

        foo = Foo()
        assert foo.bar._self is foo  # type: ignore[reportFunctionMemberAccess]


class TestWithDiDecorator:
    def test_enables_di_if_di_globally_enabled(self) -> None:
        wrapped = lightbulb.di.with_di(lambda: "foo")
        assert isinstance(wrapped, solver.AutoInjecting)

    def test_does_not_enable_di_if_di_globally_disabled(self) -> None:
        with mock.patch.object(solver, "DI_ENABLED", False):
            wrapped = lightbulb.di.with_di(func := lambda: "foo")
            assert wrapped is func
