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

__all__ = ["Marker"]


class Marker:
    """
    Simple class intended to be used in place of when you'd use an object as a marker, in order
    to provide a better repr.

    Args:
        name: The name of the marker.

    Example:

        .. code-block:: python

            >>> FOO = object()
            >>> FOO
            <object object at 0x104cdc5f0>
            >>> BAR = Marker("BAR")
            >>> BAR
            <lightbulb.Marker: BAR>
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:
        return f"<lightbulb.{self.__class__.__name__}: {self._name!r}>"
