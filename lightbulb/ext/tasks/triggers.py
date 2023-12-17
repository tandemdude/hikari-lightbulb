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

__all__ = ["Trigger", "UniformTrigger", "CronTrigger"]

import abc
import datetime
import typing as t

try:
    import croniter

    _CRON_AVAILABLE = True

except ModuleNotFoundError:
    _CRON_AVAILABLE = False

_CT = t.Union[int, str, None]


class Trigger(abc.ABC):
    """Base class representing a task trigger."""

    __slots__ = ()

    @abc.abstractmethod
    def get_interval(self) -> float:
        """
        Get the interval to sleep for in seconds until the next run of the task.

        Returns:
            :obj:`float`: Seconds to sleep until the next time the task is run.
        """
        ...

    @property
    def wait_before_execution(self) -> bool:
        """
        Whether the trigger should wait `get_interval` amount of time before executing
        for the first time by default. Will be overridden by the `wait_before_execution`
        parameter in the `task` decorator.
        """
        return False


class UniformTrigger(Trigger):
    """
    A uniform interval task trigger. Tasks will always be run with the same interval between them.

    Args:
        interval (:obj:`float`): Number of seconds between task executions.
    """

    __slots__ = ("_interval",)

    def __init__(self, interval: float) -> None:
        self._interval = interval

    def get_interval(self) -> float:
        return self._interval


if t.TYPE_CHECKING or _CRON_AVAILABLE:

    class CronTrigger(Trigger):
        """
        A crontab-based task trigger. Tasks will be run dependent on the given crontab.

        Keyword arguments are only used if no crontab expression is passed.

        Args:
            crontab (Optional[:obj:`str`]): Schedule that task executions will follow.

        Keyword Args:
            month (Optional[Union[:obj:`int`, :obj:`str`]]):
                The month(s) that the task will be executed.
            day (Optional[Union[:obj:`int`, :obj:`str`]]):
                The day(s) that the task will be executed.
            day_of_week (Optional[Union[:obj:`int`, :obj:`str`]]):
                The day(s) of the week that the task will be executed.
            hour (Optional[Union[:obj:`int`, :obj:`str`]]):
                The hour(s) that the task will be executed.
            minute (Optional[Union[:obj:`int`, :obj:`str`]]):
                The minute(s) that the task will be executed.
            second (Optional[Union[:obj:`int`, :obj:`str`]]):
                The second(s) that the task will be executed.

        Note:
            This trigger is only available when installing lightbulb with the ``[crontrigger]`` option.

            See: ``pip install hikari-lightbulb[crontrigger]``
        """

        __slots__ = ("_croniter",)

        @t.overload
        def __init__(self, crontab: str, /) -> None:
            ...

        @t.overload
        def __init__(
            self, /, *, minute: _CT = "*", hour: _CT = "*", month: _CT = "*", day_of_week: _CT = "*", second: _CT = 0
        ) -> None:
            ...

        def __init__(self, crontab: t.Optional[str] = None, /, **kwargs: _CT) -> None:
            if not crontab:
                crontab = (
                    f"{kwargs.get('minute', '*')} {kwargs.get('hour', '*')} {kwargs.get('day', '*')} "
                    f"{kwargs.get('month', '*')} {kwargs.get('day_of_week', '*')} {kwargs.get('second', 0)}"
                )

            self._croniter = croniter.croniter(crontab, datetime.datetime.now(datetime.timezone.utc))

        def get_interval(self) -> float:
            difference: datetime.timedelta = self._croniter.get_next(datetime.datetime) - datetime.datetime.now(
                datetime.timezone.utc
            )
            return difference.total_seconds()

        @property
        def wait_before_execution(self) -> bool:
            return True

else:

    class CronTrigger(Trigger):
        __slots__ = ()

        def __init__(self, _: str, /, **__: _CT) -> None:
            raise ModuleNotFoundError(
                "'CronTrigger' is not available. Install lightbulb with option '[crontrigger]' to enable"
            )

        def get_interval(self) -> float:
            raise NotImplementedError
