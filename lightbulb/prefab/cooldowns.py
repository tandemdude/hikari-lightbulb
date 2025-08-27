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
__all__ = ["CommandCooldown", "OnCooldown", "fixed_window", "sliding_window"]

import collections
import time
import typing as t
from collections.abc import Callable

import hikari
import linkd

from lightbulb import context
from lightbulb import di
from lightbulb import utils
from lightbulb.commands import execution
from lightbulb.internal import types

BucketCallable: t.TypeAlias = Callable[[context.Context], types.MaybeAwaitable[hikari.Snowflakeish]]
Bucket: t.TypeAlias = t.Union[t.Literal["global", "user", "channel", "guild"], BucketCallable]

_PROVIDED_BUCKETS: dict[str, BucketCallable] = {
    "global": lambda _: 0,
    "user": lambda ctx: ctx.user.id,
    "channel": lambda ctx: ctx.channel_id,
    "guild": lambda ctx: ctx.guild_id or ctx.channel_id,
}


class OnCooldown(Exception):
    """Exception raised when a user attempts to invoke command, but it is on cooldown."""

    def __init__(self, remaining: float) -> None:
        self.remaining: float = remaining
        """The remaining time in seconds before the command can be invoked again."""


class CommandCooldown:
    """
    Utility class registered as a dependency when a cooldown hook runs for a command. Can be
    injected into any dependency-enabled function in order to manipulate the cooldown state
    within your code.
    """

    __slots__ = ("_cls", "_ctx")

    def __init__(self, ctx: context.Context, cls: "_FixedWindow | _SlidingWindow") -> None:
        self._ctx = ctx
        self._cls = cls

    async def undo(self) -> None:
        """
        Undoes the last cooldown application for the enclosed context. If called multiple times, it will continue to
        undo each cooldown application until all have been removed.

        Returns:
            :obj:`None`
        """
        await self._cls.undo(self._ctx)

    async def reset(self) -> None:
        """
        Resets the cooldown for the enclosed context.

        Returns:
            :obj:`None`
        """
        await self._cls.reset(self._ctx)

    async def apply(self) -> None:
        """
        Applies the cooldown to the enclosed context.

        Returns:
            :obj:`None`

        Raises:
            :obj:`~OnCooldown`: If the cooldown has been exceeded.
        """
        await self._cls(None, self._ctx)  # type: ignore[reportArgumentType]


def _maybe_register_dependency(cc: CommandCooldown) -> None:
    if not di.DI_ENABLED:
        return

    di_container: linkd.Container | None = linkd.DI_CONTAINER.get(None)
    if di_container is None or di_container._tag is not di.Contexts.COMMAND:
        return

    di_container.add_value(CommandCooldown, cc)


class _FixedWindow:
    __slots__ = ("_allowed_invocations", "_bucket", "_invocations", "_window_length")

    class _InvocationData:
        __slots__ = ("expires", "n")

        def __init__(self, n: int = 0, expires: float = -1) -> None:
            self.n = n
            self.expires = expires

    def __init__(self, window_length: float, allowed_invocations: int, bucket: BucketCallable) -> None:
        self._window_length = window_length
        self._allowed_invocations = allowed_invocations
        self._bucket = bucket
        self._invocations: dict[hikari.Snowflakeish, _FixedWindow._InvocationData] = collections.defaultdict(
            _FixedWindow._InvocationData
        )

    async def undo(self, ctx: context.Context) -> None:
        data = self._invocations[await utils.maybe_await(self._bucket(ctx))]
        if data.n > 0:
            data.n -= 1

    async def reset(self, ctx: context.Context) -> None:
        self._invocations.pop(await utils.maybe_await(self._bucket(ctx)), None)

    async def __call__(self, _: execution.ExecutionPipeline, ctx: context.Context) -> None:
        _maybe_register_dependency(CommandCooldown(ctx, self))

        data = self._invocations[await utils.maybe_await(self._bucket(ctx))]
        if data.expires < (now := time.perf_counter()):
            data.expires = now + self._window_length
            data.n += 1
            return

        data.n += 1
        if data.n > self._allowed_invocations:
            raise OnCooldown(data.expires - now)


class _SlidingWindow:
    __slots__ = ("_allowed_invocations", "_bucket", "_invocations", "_window_length")

    def __init__(self, window_length: float, allowed_invocations: int, bucket: BucketCallable) -> None:
        self._window_length = window_length
        self._allowed_invocations = allowed_invocations
        self._bucket = bucket
        self._invocations: dict[hikari.Snowflakeish, list[float]] = collections.defaultdict(list)

    async def undo(self, ctx: context.Context) -> None:
        invocations = self._invocations[await utils.maybe_await(self._bucket(ctx))]
        if invocations:
            invocations.pop(-1)

    async def reset(self, ctx: context.Context) -> None:
        self._invocations.pop(await utils.maybe_await(self._bucket(ctx)), None)

    async def __call__(self, _: execution.ExecutionPipeline, ctx: context.Context) -> None:
        _maybe_register_dependency(CommandCooldown(ctx, self))

        invocations = self._invocations[hash := await utils.maybe_await(self._bucket(ctx))]
        interval = (now := time.perf_counter()) - self._window_length
        usages_in_window = [usage for usage in invocations if usage > interval]
        if len(usages_in_window) + 1 > self._allowed_invocations:
            raise OnCooldown(self._window_length - (now - usages_in_window[0]))

        self._invocations[hash] = [*usages_in_window, now]


def fixed_window(
    window_length: float,
    allowed_invocations: int,
    bucket: t.Literal["global", "user", "channel", "guild"] | BucketCallable,
) -> execution.ExecutionHook:
    """
    Creates a hook that applies a cooldown to command invocations using the :abbr:`fixed-window (The fixed-window
    rate limit algorithm tracks requests within a static time window. New request is allowed once the window
    resets.)` cooldown algorithm. The created hook raises :obj:`OnCooldown` when the cooldown is exceeded.
    This hook is run during the ``COOLDOWNS`` execution step.

    You can pass one of ``"global"``, ``"user"``, ``"channel"`` or ``"guild"`` to the ``bucket`` parameter, or
    a synchronous or asynchronous function to be used to resolve the bucket hash to apply the cooldown to.

    - ``"global"`` - every invocation of the command shares a common cooldown
    - ``"user"`` - cooldown is applied individually for each user
    - ``"channel"`` - cooldown is applied individually for each channel
    - ``"guild"`` - cooldown is applied individually for each guild. If in DMs, the cooldown is applied individually to
      each DM.

    If DI is enabled, this hook will register an instance of :obj:`~CommandCooldown` when it is executed.

    Args:
        window_length: The length of the cooldown window.
        allowed_invocations: The number of invocations allowed within one window.
        bucket: The bucket that should be used to classify invocations.

    Returns:
        The created hook.
    """
    return execution.hook(execution.ExecutionSteps.COOLDOWNS, skip_when_failed=True, name="fixed_window")(
        _FixedWindow(
            window_length, allowed_invocations, _PROVIDED_BUCKETS[bucket] if isinstance(bucket, str) else bucket
        )
    )


def sliding_window(
    window_length: float,
    allowed_invocations: int,
    bucket: Bucket,
) -> execution.ExecutionHook:
    """
    Creates a hook that applies a cooldown to command invocations using the :abbr:`sliding-window (The sliding-window
    rate limit algorithm tracks request timestamps and permits new requests within a moving time window.
    A new request is allowed once the oldest request drops out of the window.)` cooldown algorithm. The
    created hook raises :obj:`OnCooldown` when the cooldown is exceeded. This hook is run during the ``COOLDOWNS``
    execution step.

    You can pass one of ``"global"``, ``"user"``, ``"channel"`` or ``"guild"`` to the ``bucket`` parameter, or
    a synchronous or asynchronous function to be used to resolve the bucket hash to apply the cooldown to.

    - ``"global"`` - every invocation of the command shares a common cooldown
    - ``"user"`` - cooldown is applied individually for each user
    - ``"channel"`` - cooldown is applied individually for each channel
    - ``"guild"`` - cooldown is applied individually for each guild. If in DMs, the cooldown is applied individually to
      each DM.

    If DI is enabled, this hook will register an instance of :obj:`~CommandCooldown` when it is executed.

    Args:
        window_length: The length of the cooldown window.
        allowed_invocations: The number of invocations allowed within one window.
        bucket: The bucket that should be used to classify invocations.

    Returns:
        The created hook.
    """
    return execution.hook(execution.ExecutionSteps.COOLDOWNS, skip_when_failed=True, name="sliding_window")(
        _SlidingWindow(
            window_length, allowed_invocations, _PROVIDED_BUCKETS[bucket] if isinstance(bucket, str) else bucket
        )
    )
