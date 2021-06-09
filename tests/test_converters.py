import typing

import pytest
from lightbulb import commands, converters


def test_has_union_converter():
    @commands.command()
    async def test(ctx, test_arg: typing.Optional[int]):
        ...

    assert isinstance(test.arg_details.converters[0], converters._UnionConverter)


def test_has_union_converter_wrapped_in_defaulting_converter():
    @commands.command()
    async def test(ctx, test_arg: typing.Optional[int] = 1):
        ...

    converter = test.arg_details.converters[0]
    assert isinstance(converter, converters._DefaultingConverter)
    assert isinstance(converter.converter, converters._UnionConverter)


def test_has_union_converter_wrapped_in_consume_rest_converter_in_defaulting_converter():
    @commands.command()
    async def test(ctx, *, test_arg: typing.Optional[int] = 1):
        ...

    converter = test.arg_details.converters[0]
    assert isinstance(converter, converters._DefaultingConverter)
    assert isinstance(converter.converter, converters._ConsumeRestConverter)
    assert isinstance(converter.converter.converter, converters._UnionConverter)


def test_has_consume_rest_converter():
    @commands.command()
    async def test(ctx, *, test_arg: str):
        ...

    assert isinstance(test.arg_details.converters[0], converters._ConsumeRestConverter)


def test_has_defaulting_converter():
    @commands.command()
    async def test(ctx, *, test_arg: str = "test"):
        ...

    converter = test.arg_details.converters[0]
    assert isinstance(converter, converters._DefaultingConverter)
    assert isinstance(converter.converter, converters._ConsumeRestConverter)


@commands.command()
async def greedy_test1(ctx, *test_arg: int):
    ...


@commands.command()
async def greedy_test2(ctx, test_arg: converters.Greedy[int]):
    ...


@pytest.mark.parametrize("command", [greedy_test1, greedy_test2])
def test_has_greedy_converter(command):
    assert isinstance(command.arg_details.converters[0], converters._GreedyConverter)
