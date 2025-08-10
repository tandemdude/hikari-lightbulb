import enum

import lightbulb
from lightbulb import utils


class StrChoices(utils.StrEnum):
    foo = "foo"
    bar = "bar"
    baz = "baz"


class IntChoices(enum.IntEnum):
    foo = 1
    bar = 2
    baz = 3


class FloatChoices(utils.FloatEnum):
    foo = 1.5
    bar = 2.5
    baz = 3.5


def test_to_choices_sequence_of_values() -> None:
    assert utils.to_choices(["foo", "bar", "baz"]) == [
        lightbulb.Choice("foo", "foo"),
        lightbulb.Choice("bar", "bar"),
        lightbulb.Choice("baz", "baz"),
    ]
    assert utils.to_choices([1, 2, 3]) == [lightbulb.Choice("1", 1), lightbulb.Choice("2", 2), lightbulb.Choice("3", 3)]
    assert utils.to_choices([1.5, 2.5, 3.5]) == [
        lightbulb.Choice("1.5", 1.5),
        lightbulb.Choice("2.5", 2.5),
        lightbulb.Choice("3.5", 3.5),
    ]


def test_to_choices_sequence_of_tuples() -> None:
    assert utils.to_choices([("foo", "foo"), ("bar", "bar"), ("baz", "baz")]) == [
        lightbulb.Choice("foo", "foo"),
        lightbulb.Choice("bar", "bar"),
        lightbulb.Choice("baz", "baz"),
    ]
    assert utils.to_choices([("foo", 1), ("bar", 2), ("baz", 3)]) == [
        lightbulb.Choice("foo", 1),
        lightbulb.Choice("bar", 2),
        lightbulb.Choice("baz", 3),
    ]
    assert utils.to_choices([("foo", 1.5), ("bar", 2.5), ("baz", 3.5)]) == [
        lightbulb.Choice("foo", 1.5),
        lightbulb.Choice("bar", 2.5),
        lightbulb.Choice("baz", 3.5),
    ]


def test_to_choices_enums() -> None:
    assert utils.to_choices(StrChoices) == [
        lightbulb.Choice("foo", "foo"),
        lightbulb.Choice("bar", "bar"),
        lightbulb.Choice("baz", "baz"),
    ]
    assert utils.to_choices(IntChoices) == [
        lightbulb.Choice("foo", 1),
        lightbulb.Choice("bar", 2),
        lightbulb.Choice("baz", 3),
    ]
    assert utils.to_choices(FloatChoices) == [
        lightbulb.Choice("foo", 1.5),
        lightbulb.Choice("bar", 2.5),
        lightbulb.Choice("baz", 3.5),
    ]
