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
import pathlib

import msgspec
import pytest

from lightbulb import config


class SubConfig(msgspec.Struct):
    nested: str


class Config(msgspec.Struct):
    number: int
    key: int
    defaulted: str
    escaped: str
    sub: SubConfig
    items: list[SubConfig]


YAML_SAMPLE = """
number: 5
key: ${FOO}
defaulted: ${MISSING:default_val}
escaped: $${ESCAPED}
sub:
  nested: foo
items:
  - nested: bar
  - nested: baz
"""
TOML_SAMPLE = """
number = 5
key = "${FOO}"
defaulted = "${MISSING:default_val}"
escaped = "$${ESCAPED}"

[sub]
nested = "foo"

[[items]]
nested = "bar"
[[items]]
nested = "baz"
"""
JSON_SAMPLE = """
{
    "number": 5,
    "key": "${FOO}",
    "defaulted": "${MISSING:default_val}",
    "escaped": "$${ESCAPED}",
    "sub": {
        "nested": "foo"
    },
    "items": [
        {"nested": "bar"},
        {"nested": "baz"}
    ]
}
"""


@pytest.mark.parametrize(
    ["file_ext", "file_content"], [("yaml", YAML_SAMPLE), ("toml", TOML_SAMPLE), ("json", JSON_SAMPLE)]
)
def test_load(file_ext: str, file_content: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOO", "1")
    monkeypatch.delenv("MISSING", raising=False)
    monkeypatch.setenv("ESCAPED", "should_not_appear")

    file = tmp_path / f"foo.{file_ext}"
    file.write_text(file_content)

    cfg = config.load(str(file), cls=Config)
    assert cfg.number == 5
    assert cfg.key == 1
    assert cfg.defaulted == "default_val"
    assert cfg.escaped == "${ESCAPED}"
    assert cfg.sub.nested == "foo"
    assert cfg.items[0].nested == "bar"
    assert cfg.items[1].nested == "baz"


def test_load_fails_on_unknown_file_type() -> None:
    with pytest.raises(NotImplementedError):
        config.load("foo.baz", cls=Config)


def test_load_fails_when_file_cannot_parse_to_dict(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "foo.json"
    file.write_text('["foo", "bar", "baz"]')

    with pytest.raises(TypeError):
        config.load(str(file), cls=Config)
