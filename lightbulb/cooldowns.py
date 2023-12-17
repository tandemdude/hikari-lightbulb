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

__all__ = ["CooldownManager"]

import inspect
import time
import typing as t

from lightbulb import buckets
from lightbulb import cooldown_algorithms
from lightbulb import errors

if t.TYPE_CHECKING:
    from lightbulb.context import base as ctx_base


class CooldownManager:
    """The cooldown manager for a command."""

    __slots__ = ("callback", "cooldowns")

    def __init__(
        self,
        callback: t.Callable[[ctx_base.Context], t.Union[buckets.Bucket, t.Coroutine[t.Any, t.Any, buckets.Bucket]]],
    ) -> None:
        self.callback = callback
        self.cooldowns: t.MutableMapping[t.Hashable, buckets.Bucket] = {}
        """Mapping of a hashable to a :obj:`~.buckets.Bucket` representing the currently stored cooldowns."""

    async def _get_bucket(self, context: ctx_base.Context) -> buckets.Bucket:
        bucket = self.callback(context)
        if inspect.iscoroutine(bucket):
            bucket = await bucket
        assert isinstance(bucket, buckets.Bucket)
        return bucket

    async def add_cooldown(self, context: ctx_base.Context) -> None:
        """
        Add a cooldown under the given context. If an expired bucket already exists then it
        will be overwritten.

        Args:
            context (:obj:`~.context.base.Context`): The context to add a cooldown under.

        Returns:
            ``None``

        Raises:
            :obj:`~.errors.CommandIsOnCooldown`: The command is currently on cooldown for the given context.
        """
        bucket = await self._get_bucket(context)

        cooldown_hash = bucket.extract_hash(context)
        cooldown_bucket = self.cooldowns.get(cooldown_hash)

        if cooldown_bucket is not None:
            cooldown_status = cooldown_bucket.acquire()
            if inspect.iscoroutine(cooldown_status):
                cooldown_status = await cooldown_status

            if cooldown_status is cooldown_algorithms.CooldownStatus.ACTIVE:
                # Cooldown has been activated
                assert cooldown_bucket.start_time is not None
                raise errors.CommandIsOnCooldown(
                    "This command is on cooldown",
                    retry_after=(cooldown_bucket.start_time + cooldown_bucket.length) - time.perf_counter(),
                )
            elif cooldown_status is cooldown_algorithms.CooldownStatus.INACTIVE:
                # Cooldown has not yet been activated.
                return

        self.cooldowns[cooldown_hash] = bucket
        maybe_coro = self.cooldowns[cooldown_hash].acquire()
        if inspect.iscoroutine(maybe_coro):
            await maybe_coro

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
