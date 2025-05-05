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
"""
This module contains utilities for parsing your application configuration from various file types. Along with
basic deserializing to Python objects, it implements environment variable substitution expressions to allow
"dynamic" values within the configuration.

.. note::
    Using this feature requires that you have `msgspec <https://jcristharif.com/msgspec/>`_ installed.

Environment Variable Substitution
---------------------------------

The basic syntax for defining a variable substitution is as follows:

.. code-block:: yaml

    ${VARIABLE_NAME}

This would be replaced by the loader with the value of the environment variable ``VARIABLE_NAME`` while parsing
the configuration. If the variable is not set, then this will evaluate to an empty string.

Expanding on this, you can also specify default values for when a variable is not set:

.. code-block:: yaml

    ${VARIABLE_NAME:default-value}

This will expand to the value of ``VARIABLE_NAME``, if it is set, otherwise it will expand to whatever you specified
as the default value.

Sometimes you may want to include text that uses the ``${NAME}`` format directly, without any substitution. This
can be achieved by escaping the substitution expression with an additional ``$`` symbol:

.. code-block:: yaml

    $${VARIABLE_NAME}

This will not be expanded using the environment variables, and instead one of the leading ``$`` symbols will be
stripped, causing it to evaluate as ``${VARIABLE_NAME}``.

Usage
-----

You should create a configuration file for your application - supported
formats are ``yaml``, ``toml`` and ``json`` - and a :obj:`msgspec.Struct`-derived class that your configuration
will be deserialized to.

``config.yaml``

.. code-block:: yaml

    foo: bar
    baz: ${INT_VAR}
    bork:
      qux: quux

``config.py``

.. code-block:: python

    class BorkConfig(msgspec.Struct):
        qux: str

    class Config(msgspec.Struct):
        foo: str
        baz: int
        bork: BorkConfig

Then to parse the config file into your models, simply call the :meth:`~load` method:

.. code-block:: python

    import lightbulb
    # your configuration models
    from app import config

    parsed_cfg = lightbulb.config.load("path/to/config.yaml", cls=config.Config)
    # prints "bar"
    print(parsed_cfg.foo)
"""

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

    Raises:
        :obj:`NotImplementedError`: If a file with an unrecognized format is specified.
        :obj:`ValueError`: If the file cannot be parsed to a dictionary (e.g. the top level object is an array).
        :obj:`ImportError`: If a required dependency is not installed.
    """
    try:
        import msgspec
    except ImportError as e:  # pragma: no cover
        raise ImportError("'msgspec' is a required dependency when using lightbulb config loading") from e

    parser: Callable[[bytes], t.Any]
    if path.endswith(".yaml") or path.endswith(".yml"):
        try:
            import ruamel.yaml as yaml
        except ImportError as e:  # pragma: no cover
            raise ImportError("'ruamel.yaml' is required for '.yaml' file support") from e
        parser = yaml.YAML(typ="safe", pure=True).load  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]
    elif path.endswith(".json"):
        parser = msgspec.json.decode
    elif path.endswith(".toml"):
        parser = msgspec.toml.decode
    else:
        raise NotImplementedError(f"{path.split('.')[-1]!r} files are not supported")

    with open(path, "rb") as fp:
        parsed = parser(fp.read())  # type: ignore[reportUnknownVariableType]

    if not isinstance(parsed, dict):
        raise TypeError("top-level config must be parseable to dict")

    substituted = _substitute_config(t.cast("dict[t.Any, t.Any]", parsed))
    return msgspec.json.decode(msgspec.json.encode(substituted), type=cls, strict=False, dec_hook=dec_hook)
