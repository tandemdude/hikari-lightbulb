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
from lightbulb.di.solver import parse_injectable_kwargs


class TestSignatureParsing:
    def test_does_not_parse_positional_only_args(self) -> None:
        def m(foo: object, /) -> None: ...

        pos, kw = parse_injectable_kwargs(m)
        assert len(pos) == 0 and len(kw) == 0

    def test_does_not_parse_var_positional_args(self) -> None:
        def m(*foo: object) -> None: ...

        pos, kw = parse_injectable_kwargs(m)
        assert len(pos) == 0 and len(kw) == 0

    def test_does_not_parse_var_kw_args(self) -> None:
        def m(**foo: object) -> None: ...

        pos, kw = parse_injectable_kwargs(m)
        assert len(pos) == 0 and len(kw) == 0

    def test_does_not_parse_args_with_non_INJECTED_default(self) -> None:  # noqa: N802
        def m(foo: object = object()) -> None: ...

        pos, kw = parse_injectable_kwargs(m)
        assert len(pos) == 0 and len(kw) == 0

    def test_does_not_parse_args_with_no_annotation(self) -> None:
        def m(foo) -> None:  # type: ignore[unknownParameterType]
            ...

        pos, kw = parse_injectable_kwargs(m)  # type: ignore[unknownArgumentType]
        assert len(pos) == 0 and len(kw) == 0

    def test_parses_args_correctly(self) -> None:
        def m(
            foo: str, bar: int = lightbulb.di.INJECTED, *, baz: float, bork: bool = lightbulb.di.INJECTED
        ) -> None: ...

        pos, kw = parse_injectable_kwargs(m)

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

        with pytest.raises(RuntimeError):
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
