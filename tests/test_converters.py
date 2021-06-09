import typing

import pytest
from lightbulb import commands, converters


def assert_converters_recursively(
    converter: typing.Optional[converters._BaseConverter],
    types: typing.Sequence[typing.Type[converters._BaseConverter]],
    idx: int = 0,
) -> None:
    if converter is None:
        return

    assert isinstance(converter, types[idx])

    try:
        return getattr(converter, "converter", None)
    finally:
        idx += 1


@commands.command()
async def union_test1(ctx, test_arg: typing.Optional[int]):
    ...


@commands.command()
async def union_test2(ctx, test_arg: typing.Optional[int] = 1):
    ...


@pytest.mark.parametrize("command", [union_test1, union_test2])
def test_has_union_converter_wrapped_in_defaulting_converter(command):
    converter_types = [converters._DefaultingConverter, converters._UnionConverter]
    assert_converters_recursively(command.arg_details.converters[0], converter_types)


def test_has_union_converter_wrapped_in_consume_rest_converter_in_defaulting_converter():
    @commands.command()
    async def test(ctx, *, test_arg: typing.Optional[int] = 1):
        ...

    converter_types = [
        converters._DefaultingConverter,
        converters._ConsumeRestConverter,
        converters._DefaultingConverter,
        converters._UnionConverter,
    ]
    assert_converters_recursively(test.arg_details.converters[0], converter_types)


def test_has_consume_rest_converter():
    @commands.command()
    async def test(ctx, *, test_arg: str):
        ...

    assert isinstance(test.arg_details.converters[0], converters._ConsumeRestConverter)


def test_has_defaulting_converter():
    @commands.command()
    async def test(ctx, *, test_arg: str = "test"):
        ...

    converter_types = [converters._DefaultingConverter, converters._ConsumeRestConverter]
    assert_converters_recursively(test.arg_details.converters[0], converter_types)


@commands.command()
async def greedy_test1(ctx, *test_arg: int):
    ...


@commands.command()
async def greedy_test2(ctx, test_arg: converters.Greedy[int]):
    ...


@pytest.mark.parametrize("command", [greedy_test1, greedy_test2])
def test_has_greedy_converter(command):
    assert isinstance(command.arg_details.converters[0], converters._GreedyConverter)
