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

__all__ = [
    "CooldownStatus",
    "CooldownAlgorithm",
    "BangBangCooldownAlgorithm",
    "FixedWindowCooldownAlgorithm",
    "SlidingWindowCooldownAlgorithm",
]

import abc
import enum
import time
import typing as t

from lightbulb import errors

if t.TYPE_CHECKING:
    from lightbulb import buckets


class CooldownStatus(enum.Enum):
    INACTIVE = enum.auto()
    ACTIVE = enum.auto()
    EXPIRED = enum.auto()


class CooldownAlgorithm(abc.ABC):
    """
    Base class that represents an algorithm that can be used to calculate whether a command
    is on cooldown or not.
    """

    __slots__ = ()

    @abc.abstractmethod
    def evaluate(self, bucket: buckets.Bucket) -> t.Union[CooldownStatus, t.Coroutine[t.Any, t.Any, CooldownStatus]]:
        """
        Evaluate whether the command should be on cooldown given internal state of this object and
        the bucket object passed in.

        Args:
            bucket (:obj:`~.buckets.Bucket`): The bucket to process the cooldown for.

        Returns:
            :obj:`~CooldownStatus`: The status of the cooldown.
        """
        ...


class BangBangCooldownAlgorithm(CooldownAlgorithm):
    """
    Cooldown algorithm that allows ``n`` command invocations to be used, and then waits for the appropriate
    amount of time before allowing any additional invocations.
    """

    __slots__ = ("_commands_run",)

    def __init__(self) -> None:
        self._commands_run: int = 0

    def evaluate(self, bucket: buckets.Bucket) -> CooldownStatus:
        self._commands_run += 1
        if self._commands_run >= bucket.usages:
            bucket.activate()
        return CooldownStatus.INACTIVE


class FixedWindowCooldownAlgorithm(CooldownAlgorithm):
    """
    Cooldown algorithm that allows ``n`` command invocations within a fixed window time period. I.e. 5 invocations
    within a 30-second time period, allowing additional invocations once the entire period has elapsed.
    """

    __slots__ = ("_commands_run", "_expires")

    def __init__(self) -> None:
        self._commands_run: int = 0
        self._expires: t.Optional[float] = None

    def evaluate(self, bucket: buckets.Bucket) -> CooldownStatus:
        self._expires = self._expires or (time.perf_counter() + bucket.length)
        if self._expires > time.perf_counter():
            self._commands_run = 0

        self._commands_run += 1
        if self._commands_run > bucket.usages:
            raise errors.CommandIsOnCooldown(
                "This command is on cooldown", retry_after=(self._expires - time.perf_counter())
            )
        return CooldownStatus.INACTIVE


class SlidingWindowCooldownAlgorithm(CooldownAlgorithm):
    """
    Cooldown algorithm that allows ``n`` command invocations within a sliding window time period. I.e. 5 invocations
    within the last 30 seconds will allow an extra invocation every time the earliest invocation falls out of the
    window.
    """

    __slots__ = ("_prev_usages",)

    def __init__(self) -> None:
        self._prev_usages: t.List[float] = []

    def evaluate(self, bucket: buckets.Bucket) -> CooldownStatus:
        interval = time.perf_counter() - bucket.length
        # Find the usages that would be within the current window
        usages_in_window = [usage for usage in self._prev_usages[::-1] if usage > interval]
        if len(usages_in_window) + 1 > bucket.usages:
            raise errors.CommandIsOnCooldown(
                "This command is on cooldown", retry_after=bucket.length - (time.perf_counter() - usages_in_window[0])
            )
        # Replace the stored usages so that the list doesn't grow forever
        self._prev_usages = usages_in_window
        self._prev_usages.append(time.perf_counter())
        return CooldownStatus.INACTIVE
