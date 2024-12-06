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
__all__ = ["MaxConcurrencyReached", "max_concurrency"]

import collections

import hikari  # noqa: TC002

from lightbulb import context
from lightbulb import utils
from lightbulb.commands import execution
from lightbulb.prefab.cooldowns import _PROVIDED_BUCKETS
from lightbulb.prefab.cooldowns import Bucket


class MaxConcurrencyReached(Exception):
    """Exception raised when a user attempts to invoke a command, but the concurrency limit has been reached."""


def max_concurrency(n_invocations: int, bucket: Bucket) -> tuple[execution.ExecutionHook, execution.ExecutionHook]:
    """
    Creates hooks that enforce a concurrency limit for a **single** command. The created hooks raise
    :obj:`~MaxConcurrencyReached` when they fail. The created hooks are run during the ``MAX_CONCURRENCY`` and
    ``POST_INVOKE`` execution steps. As this returns **multiple** hooks, you should unpack them into the hooks list
    for your command - see the example for details.

    Args:
        n_invocations: The number of invocations permitted to be running at the same time.
        bucket: The bucket which invocations should be limited within. Accepts the same values that the
            cooldowns do.

    Returns:
        The created hooks.

    Warning:
        **DO NOT** use the same hooks for multiple commands - this will cause the concurrency limit to be
        shared between them. Make sure you call this function a single time for each command you wish to enforce
        a concurrency limit with.

    Warning:
        If you add any other checks for the ``POST_INVOKE`` execution step, you should probably specify them
        before these in the hooks list for the command - otherwise the concurrency limit will be decreased before
        the other ``POST_INVOKE`` hooks have been run.

    Example:

        .. code-block:: python

            class YourCommand(
                ...,
                hooks=[..., *lightbulb.prefab.max_concurrency(1, "global")]
            ):
                ...
    """
    invocations: dict[hikari.Snowflakeish, int] = collections.defaultdict(lambda: 0)
    bucket_callable = _PROVIDED_BUCKETS[bucket] if isinstance(bucket, str) else bucket

    @execution.hook(execution.ExecutionSteps.MAX_CONCURRENCY, name="incr_concurrency")
    async def _increment_invocation_count(_: execution.ExecutionPipeline, ctx: context.Context) -> None:
        if invocations[hash := await utils.maybe_await(bucket_callable(ctx))] >= n_invocations:
            raise MaxConcurrencyReached

        invocations[hash] += 1

    @execution.hook(execution.ExecutionSteps.POST_INVOKE, name="decr_concurrency")
    async def _decrement_invocation_count(_: execution.ExecutionPipeline, ctx: context.Context) -> None:
        invocations[hash] = min(invocations[hash := await utils.maybe_await(bucket_callable(ctx))] - 1, 0)

    return _increment_invocation_count, _decrement_invocation_count
