# -*- coding: utf-8 -*-
# Copyright © tandemdude 2020-present
#
# This file is part of Lightbulb.
#
# Lightbulb is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Lightbulb is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Lightbulb. If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

__all__ = ["DataStore"]

import typing as t

T = t.TypeVar("T")


class DataStore(t.Dict[str, t.Any]):
    """
    Data storage class allowing setting, retrieval and unsetting of custom
    attributes. This class subclasses :obj:`dict` so the data can be accessed the same
    as you would a dictionary as well as using dot notation.

    Example:

        .. code-block:: python

            >>> d = DataStore()
            >>> d.foo = "bar"
            >>> d.foo
            'bar'
            >>> d["foo"]
            'bar'
            >>> d
            DataStore(foo='bar')
            >>> d.pop("foo")
            'bar'
            >>> d
            DataStore()

    A DataStore instance is attached to :obj:`~.app.BotApp` instances as :attr:`bot.d <.app.BotApp.d>` for your convenience.
    """  # noqa: E501 (line-too-long)

    __slots__ = ()

    def __repr__(self) -> str:
        return "DataStore(" + ", ".join(f"{k}={v!r}" for k, v in self.items()) + ")"

    def __getattr__(self, item: str) -> t.Any:
        return self.get(item)

    def __setattr__(self, key: str, value: t.Any) -> None:
        self[key] = value

    def __delattr__(self, item: str) -> None:
        self.pop(item, None)

    def get_as(self, item: str, type: t.Type[T]) -> T:
        """
        Helper method to allow type-complete getting of items from this ``DataStore``.

        Args:
            item (:obj:`str`): The name of the key that the item is stored at.
            type (Type[T]): The type to cast the item as.

        Returns:
            T: The item stored at key ``item``, cast to the given type.

        Raises:
            :obj:`ValueError`: If a key of name ``item`` has not been set.

        Note:
            This does **not** verify types, it just performs a :meth:`typing.cast` to fool the
            type system into thinking that the return value is of the correct type.

        .. versionadded:: 2.2.4
        """
        if item not in self:
            raise TypeError(f"Item {item!r} was never set")
        return t.cast(T, self.get(item))
