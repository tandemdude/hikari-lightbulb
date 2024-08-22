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

import pytest

import lightbulb
from lightbulb.di import solver
from lightbulb.di.solver import ParamInfo
from lightbulb.di.solver import _parse_injectable_params


class TestSignatureParsing:
    def test_parses_positional_only_arg_correctly(self) -> None:
        def m(foo: object, /) -> None: ...

        pos, kw = _parse_injectable_params(m)
        assert not pos[0].injectable and len(kw) == 0

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
        assert not pos[0].injectable and len(kw) == 0

    def test_parses_args_with_no_annotation_correctly(self) -> None:
        def m(foo) -> None:  # type: ignore[unknownParameterType]
            ...

        pos, kw = _parse_injectable_params(m)  # type: ignore[unknownArgumentType]
        assert not pos[0].injectable and len(kw) == 0

    def test_parses_args_correctly(self) -> None:
        def m(
            foo: str,
            bar: int | float = lightbulb.di.INJECTED,
            *,
            baz: float | None,
            bork: t.Union[bool, object] = lightbulb.di.INJECTED,
            qux: t.Optional[object] = lightbulb.di.INJECTED,
        ) -> None: ...

        pos, kw = _parse_injectable_params(m)

        assert pos == [ParamInfo("foo", (str,), False, True), ParamInfo("bar", (int, float), False, True)]
        assert kw == [
            ParamInfo("baz", (float,), True, True),
            ParamInfo("bork", (bool, object), False, True),
            ParamInfo("qux", (object,), True, True),
        ]


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

    @pytest.mark.asyncio
    async def test_None_provided_if_dependency_not_available_for_optional_parameter(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        @lightbulb.di.with_di
        async def m(foo: object | None = lightbulb.di.INJECTED) -> None:
            assert foo is None

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_second_dependency_provided_if_first_not_available(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        value = object()
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, value)

        @lightbulb.di.with_di
        async def m(foo: str | object = lightbulb.di.INJECTED) -> None:
            assert foo is value

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_first_dependency_provided_if_both_are_available(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(str, "bar")
        manager.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(object, object())

        @lightbulb.di.with_di
        async def m(foo: str | object = lightbulb.di.INJECTED) -> None:
            assert foo == "bar"

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_None_provided_if_no_dependencies_available(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        @lightbulb.di.with_di
        async def m(foo: str | object | None = lightbulb.di.INJECTED) -> None:
            assert foo is None

        async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
            await m()

    @pytest.mark.asyncio
    async def test_exception_raised_when_no_dependencies_available(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        @lightbulb.di.with_di
        async def m(foo: str | object = lightbulb.di.INJECTED) -> None: ...

        with pytest.raises(lightbulb.di.DependencyNotSatisfiableException):
            async with manager.enter_context(lightbulb.di.Contexts.DEFAULT):
                await m()


class TestLazyInjecting:
    def test_getattr_passes_through_to_function(self) -> None:
        @lightbulb.di.with_di
        def m() -> None: ...

        assert m.__name__ == "m"

    def test_setattr_passes_through_to_function(self) -> None:
        def m() -> None: ...

        fn = lightbulb.di.with_di(m)
        fn.__lb_foo__ = "bar"  # type: ignore[reportFunctionMemberAccess]

        assert m.__lb_foo__ == "bar"  # type: ignore[reportFunctionMemberAccess]

    def test__get__within_class_does_not_assign_self(self) -> None:
        class Foo:
            @lightbulb.di.with_di
            def m(self) -> None: ...

        assert Foo.m._self is None  # type: ignore[reportFunctionMemberAccess]


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

        async with manager.enter_context(lightbulb.di.Contexts.COMMAND):
            pass

        assert manager.default_container is not None
        assert not manager.default_container._closed

    @pytest.mark.asyncio
    async def test_default_container_closed_once_manager_closed(self) -> None:
        manager = lightbulb.di.DependencyInjectionManager()

        async with manager.enter_context(lightbulb.di.Contexts.COMMAND):
            pass

        assert manager.default_container is not None
        default_container = manager.default_container

        await manager.close()
        assert default_container._closed
        assert manager.default_container is None


class TestWithDiDecorator:
    def test_does_not_enable_injection_when_injection_already_enabled(self) -> None:
        method = lightbulb.di.with_di(lambda: None)
        assert lightbulb.di.with_di(method) is method

    def test_does_not_enable_injection_when_injection_globally_disabled(self) -> None:
        solver.DI_ENABLED = False
        method = lambda: None  # noqa: E731
        assert lightbulb.di.with_di(method) is method
        solver.DI_ENABLED = True
