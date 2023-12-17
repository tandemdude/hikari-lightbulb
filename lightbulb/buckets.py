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

__all__ = ["Bucket", "UserBucket", "GuildBucket", "GlobalBucket", "ChannelBucket"]

import abc
import time
import typing as t

from lightbulb import cooldown_algorithms

if t.TYPE_CHECKING:
    from lightbulb.context import base as ctx_base


class Bucket(abc.ABC):
    """
    Base class that represents a bucket that cooldowns or max concurrency limits can
    be applied under. All buckets must inherit from this class.

    Note that for max concurrency limiting, the bucket object will never be instantiated.

    Args:
        length (:obj:`float`): Length of the cooldown timer.
        max_usages (:obj:`int`): Number of command usages before the cooldown is activated.
    """

    __slots__ = ("length", "usages", "cooldown_algorithm", "activated", "start_time")

    def __init__(
        self,
        length: float,
        max_usages: int,
        cooldown_algorithm: t.Type[
            cooldown_algorithms.CooldownAlgorithm
        ] = cooldown_algorithms.BangBangCooldownAlgorithm,
    ) -> None:
        self.length = length
        self.usages = max_usages
        self.cooldown_algorithm = cooldown_algorithm()
        self.activated = False
        self.start_time: t.Optional[float] = None
        """The start time of the bucket cooldown. This is relative to :meth:`time.perf_counter`."""

    @classmethod
    @abc.abstractmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        """
        Extracts the hash from the context which links a command usage to a single bucket.

        Args:
            context (:obj:`~.context.base.Context`): The context the command was invoked under.

        Returns:
            Hashable: Hashable object linking the context to a bucket.
        """
        ...

    def acquire(
        self,
    ) -> t.Union[cooldown_algorithms.CooldownStatus, t.Coroutine[t.Any, t.Any, cooldown_algorithms.CooldownStatus]]:
        """
        Get the current state of the cooldown and add a command usage if the cooldown is not
        currently active or has expired.

        This method is **only** used when processing cooldowns.

        Returns:
            :obj:`~CooldownStatus`: The status of the cooldown bucket.
        """
        if self.active:
            return cooldown_algorithms.CooldownStatus.ACTIVE
        elif self.activated and self.expired:
            return cooldown_algorithms.CooldownStatus.EXPIRED

        return self.cooldown_algorithm.evaluate(self)

    @property
    def active(self) -> bool:
        """Whether the cooldown represented by the bucket is currently active."""
        return self.activated and not self.expired

    @property
    def expired(self) -> bool:
        """Whether the cooldown represented by the bucket has expired."""
        if self.start_time is not None:
            return time.perf_counter() >= (self.start_time + self.length)
        return True

    def activate(self) -> None:
        self.activated = True
        self.start_time = time.perf_counter()


class GlobalBucket(Bucket):
    """
    Global bucket. All cooldowns and concurrency limits will
    be applied globally if you use this bucket.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return 0


class UserBucket(Bucket):
    """
    User bucket. All cooldowns and concurrency limits will
    be applied per user if you use this bucket.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return context.author.id


class ChannelBucket(Bucket):
    """
    Channel bucket. All cooldowns and concurrency limits will
    be applied per channel if you use this bucket.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return context.channel_id


class GuildBucket(Bucket):
    """
    Guild bucket. All cooldowns and concurrency limits will be applied per guild
    if you use this bucket. The command will still be permitted to be run in DMs in which
    case the DM channel ID will be used as the cooldown identifier instead of a guild ID.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return context.guild_id if context.guild_id is not None else context.channel_id
