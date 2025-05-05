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
from __future__ import annotations

__all__ = ["load"]

import os
import re
import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Callable

    import msgspec

StructT = t.TypeVar("StructT", bound="msgspec.Struct")

ENV_VAR_REGEX = re.compile(r"(?P<escaped>\$)?(?P<raw>\${(?P<name>[a-zA-Z_]\w*)(?P<default>:[^}]*)?})")


def _try_substitute_value(value: t.Any) -> t.Any:
    if not isinstance(value, str):
        return value

    def _replace(match: re.Match[str]) -> str:
        if match.group("escaped"):
            return str(match.group("raw"))

        var, is_set = os.getenv(name := match.group("name")), name in os.environ
        if not is_set and (default := match.group("default")):
            return str(default)[1:]  # strip the leading colon

        return str(var)

    return ENV_VAR_REGEX.sub(_replace, value)


def _substitute_config(config: dict[t.Any, t.Any]) -> dict[t.Any, t.Any]:
    def process_item(value: t.Any) -> t.Any:
        if isinstance(value, dict):
            return process_dict(t.cast("dict[t.Any, t.Any]", value))
        elif isinstance(value, list):
            return process_list(t.cast("list[t.Any]", value))
        else:
            return _try_substitute_value(value)

    def process_dict(dct: dict[t.Any, t.Any]) -> dict[t.Any, t.Any]:
        for k, v in dct.items():
            dct[k] = process_item(v)

        return dct

    def process_list(lst: list[t.Any]) -> list[t.Any]:
        for i in range(len(lst)):
            lst[i] = process_item(lst[i])
        return lst

    return process_item(config)


def load(path: str, *, cls: type[StructT], dec_hook: Callable[[type[t.Any], t.Any], t.Any] | None = None) -> StructT:
    """
    Loads arbitrary configuration from the given path, performing environment variable substitutions, and
    parses it into the given msgspec Struct class. Currently supported formats are: yaml, toml and JSON.

    Args:
        path: The path to the configuration file.
        cls: The msgspec Struct to parse the configuration into.
        dec_hook: Optional decode hook for msgspec to use when parsing to allow supporting additional types.

    Returns:
        The parsed configuration.
    """
    try:
        import msgspec
    except ImportError as e:
        raise RuntimeError("'msgspec' is a required dependency when using lightbulb config loading") from e

    parser: Callable[[bytes], t.Any]
    if path.endswith(".yaml") or path.endswith(".yml"):
        try:
            import ruamel.yaml as yaml
        except ImportError as e:
            raise RuntimeError("'ruamel.yaml' is required for '.yaml' file support") from e
        parser = yaml.YAML(typ="safe", pure=True).load  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
    elif path.endswith(".json"):
        parser = msgspec.json.decode
    elif path.endswith(".toml"):
        parser = msgspec.toml.decode
    else:
        raise ValueError(f"{path.split('.')[-1]!r} files are not supported")

    with open(path, "rb") as fp:
        parsed = t.cast("t.Any", parser(fp.read()))

    if not isinstance(parsed, dict):
        raise RuntimeError("top-level config must be parseable to dict")

    substituted = _substitute_config(t.cast("dict[t.Any, t.Any]", parsed))
    return msgspec.json.decode(msgspec.json.encode(substituted), type=cls, strict=False, dec_hook=dec_hook)
