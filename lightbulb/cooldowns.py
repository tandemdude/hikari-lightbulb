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

__all__ = ["CooldownStatus", "Bucket", "UserBucket", "GuildBucket", "GlobalBucket", "ChannelBucket", "CooldownManager"]

import abc
import enum
import inspect
import time
import typing as t

from lightbulb import errors

if t.TYPE_CHECKING:
    from lightbulb.context import base as ctx_base


class CooldownStatus(enum.Enum):
    INACTIVE = enum.auto()
    ACTIVE = enum.auto()
    EXPIRED = enum.auto()


class Bucket(abc.ABC):
    """
    Base class for representing a cooldown bucket. All buckets should inherit from this class.

    Args:
        length (:obj:`float`): Length of the cooldown timer.
        max_usages (:obj:`int`): Number of command usages before the cooldown is activated.
    """

    __slots__ = ("length", "usages", "commands_run", "activated", "start_time")

    def __init__(self, length: float, max_usages: int) -> None:
        self.length = length
        self.usages = max_usages
        self.commands_run: int = 0
        """Commands run for this bucket since it was created."""
        self.activated = False
        self.start_time: t.Optional[float] = None
        """The start time of the bucket cooldown. This is relative to :meth:`time.perf_counter`."""

    @classmethod
    @abc.abstractmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        """
        Extracts the hash from the context which links a command usage to a single cooldown bucket.

        Args:
            context (:obj:`~.context.base.Context`): The context the command was invoked under.

        Returns:
            Hashable: Hashable object linking the context to a cooldown bucket.
        """
        ...

    def acquire(self) -> CooldownStatus:
        """
        Get the current state of the cooldown and add a command usage if the cooldown is not
        currently active or has expired.

        Returns:
            :obj:`~CooldownStatus`: The status of the cooldown bucket.
        """
        if self.active:
            return CooldownStatus.ACTIVE
        elif self.activated and self.expired:
            return CooldownStatus.EXPIRED

        self.commands_run += 1
        if self.commands_run >= self.usages:
            self.activated = True
            self.start_time = time.perf_counter()
        return CooldownStatus.INACTIVE

    @property
    def active(self) -> bool:
        """
        Whether or not the cooldown represented by the bucket is currently active.
        """
        return self.activated and not self.expired

    @property
    def expired(self) -> bool:
        """
        Whether or not the cooldown represented by the bucket has expired.
        """
        if self.start_time is not None:
            return time.perf_counter() >= (self.start_time + self.length)
        return True


class GlobalBucket(Bucket):
    """
    Global cooldown bucket. All cooldowns will be applied globally if you use this bucket.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return 0


class UserBucket(Bucket):
    """
    User cooldown bucket. All cooldowns will be applied per user if you use this bucket.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return context.author.id


class ChannelBucket(Bucket):
    """
    Channel cooldown bucket. All cooldowns will be applied per channel if you use this bucket.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return context.channel_id


class GuildBucket(Bucket):
    """
    Guild cooldown bucket. All cooldowns will be applied per guild if you use this bucket. The command will
    still be permitted to be run in DMs in which case the DM channel ID will be used as the cooldown identifier
    instead of a guild ID.
    """

    __slots__ = ()

    @classmethod
    def extract_hash(cls, context: ctx_base.Context) -> t.Hashable:
        return context.guild_id if context.guild_id is not None else context.channel_id


class CooldownManager:
    """
    The cooldown manager for a command.
    """

    __slots__ = ("callback", "cooldowns")

    def __init__(
        self,
        callback: t.Callable[[ctx_base.Context], t.Union[Bucket, t.Coroutine[t.Any, t.Any, Bucket]]],
    ) -> None:
        self.callback = callback
        self.cooldowns: t.MutableMapping[t.Hashable, Bucket] = {}
        """Mapping of a hashable to a :obj:`~Bucket` representing the currently stored cooldowns."""

    async def _get_bucket(self, context: ctx_base.Context) -> Bucket:
        bucket = self.callback(context)
        if inspect.iscoroutine(bucket):
            bucket = await bucket
        assert isinstance(bucket, Bucket)
        return bucket

    async def add_cooldown(self, context: ctx_base.Context) -> None:
        """
        Add a cooldown under the given context. If an expired bucket already exists then it
        will be overwritten.

        Args:
            context (:obj:`~.context.base.Context`): The context to add a cooldown under.

        Returns:
            ``None``
        """
        bucket = await self._get_bucket(context)

        cooldown_hash = bucket.extract_hash(context)
        cooldown_bucket = self.cooldowns.get(cooldown_hash)

        if cooldown_bucket is not None:
            cooldown_status = cooldown_bucket.acquire()
            if cooldown_status is CooldownStatus.ACTIVE:
                # Cooldown has been activated
                assert cooldown_bucket.start_time is not None
                raise errors.CommandIsOnCooldown(
                    "This command is on cooldown",
                    retry_after=(cooldown_bucket.start_time + cooldown_bucket.length) - time.perf_counter(),
                )
            elif cooldown_status is CooldownStatus.INACTIVE:
                # Cooldown has not yet been activated.
                return

        self.cooldowns[cooldown_hash] = bucket
        self.cooldowns[cooldown_hash].acquire()

    async def reset_cooldown(self, context: ctx_base.Context) -> None:
        """
        Reset the cooldown under the given context.

        Args:
            context (:obj:`~.context.base.Context`): The context to reset the cooldown under.

        Returns:
            ``None``
        """
        bucket = await self._get_bucket(context)
        del self.cooldowns[bucket.extract_hash(context)]
