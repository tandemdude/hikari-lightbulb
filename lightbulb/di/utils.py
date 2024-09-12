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

__all__ = ["get_dependency_id"]

import functools
import typing as t
from collections.abc import Sequence


@functools.cache
def get_dependency_id(dependency_type: t.Any) -> str:
    """
    Get the dependency id of the given type. This is used when storing and retrieving dependencies from registries
    and containers.

    Args:
        dependency_type: The type to get the dependency id for.

    Returns:
        The dependency id for the given type.
    """
    root_id = (mod + ".") if (mod := dependency_type.__module__) != "builtins" else ""
    root_id += getattr(dependency_type, "__qualname__", dependency_type.__name__)

    if not (args := t.get_args(dependency_type)):
        return root_id

    str_args: list[str] = []
    for arg in args:
        if isinstance(arg, Sequence):
            str_args.append(f"[{','.join(get_dependency_id(a) for a in arg)}]")  # type: ignore[reportUnknownVariableType]
            continue

        str_args.append(get_dependency_id(arg))

    return f"{root_id}[{','.join(str_args)}]"
