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

        assert pos == [("foo", str), ("bar", int)]
        assert kw == {"baz": float, "bork": bool}


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
