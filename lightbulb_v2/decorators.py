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

__all__ = ["implements", "command", "option"]

import typing as t

import hikari

from lightbulb_v2 import commands

if t.TYPE_CHECKING:
    from lightbulb_v2 import checks as checks_
    from lightbulb_v2 import context

T = t.TypeVar("T")


def implements(
    *command_types: t.Type[commands.base.Command],
) -> t.Callable[
    [t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]],
    t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]],
]:
    """
    Second order decorator that defines the command types that a given callback function will implement.

    Args:
        *command_types (Type[:obj:`~.commands.base.Command`]): Command types that the function will implement.
    """

    def decorate(
        func: t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]
    ) -> t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]:
        setattr(func, "__cmd_types__", command_types)
        return func

    return decorate


def command(
    name: str, description: str, **kwargs: t.Any
) -> t.Callable[[t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]], commands.base.CommandLike]:
    """
    Second order decorator that converts the decorated function into a :obj:`~.commands.base.CommandLike` object.

    Args:
        name (:obj:`str`): The name of the command .
        description (:obj:`str`): The description of the command.

    Keyword Args:
        cooldown_manager (Optional[...]): The cooldown manager to use for the command. Defaults to ``None``.
        error_handler (Optional[ListenerT]): The function to register as the command's error handler. Defaults to
            ``None``. This can also be set with the :obj:`~.commands.base.CommandLike.set_error_handler`
            decorator.
        aliases (Sequence[:obj:`str`]): Aliases for the command. This will only affect prefix commands. Defaults
            to an empty list.
        guilds (Sequence[:obj:`int`]): The guilds that the command will be created in. This will only affect
            application commands. Defaults to an empty list.
    """

    def decorate(
        func: t.Callable[[context.base.Context], t.Coroutine[t.Any, t.Any, None]]
    ) -> commands.base.CommandLike:
        return commands.base.CommandLike(func, name, description, **kwargs)

    return decorate


def option(
    name: str, description: str, type: t.Type[t.Any] = str, **kwargs: t.Any
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that adds an option to the decorated :obj:`~.commands.base.CommandLike`
    object.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        type (Type[Any]): The type of the option. This will be used as the converter for prefix commands.

    Keyword Args:
        required (:obj:`bool`): Whether or not this option is required. This will be inferred from whether or not
            a default was provided if unspecified.
        choices (Optional[Sequence[Union[:obj:`str`, :obj:`int`, :obj:`float`, :obj:`~hikari.commands.CommandChoice`]]]): The
            choices for the option. This will only affect application (slash) commands. Defaults to ``None``.
        channel_types (Optional[Sequence[hikari.channels.ChannelType]]): The channel types allowed for the option.
            This will only affect application (slash) commands. Defaults to ``None``.
        default (UndefinedOr[Any]): The default value for the option. Defaults to :obj:`~hikari.undefined.UNDEFINED`.
        modifier (:obj:`~.commands.base.OptionModifier`): Modifier controlling how the option should be parsed. Defaults
            to ``OptionModifier.NONE``.
    """
    kwargs.setdefault("required", kwargs.get("default", hikari.UNDEFINED) is hikari.UNDEFINED)

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        c_like.options[name] = commands.base.OptionLike(name, description, type, **kwargs)
        return c_like

    return decorate


def checks(*cmd_checks: checks_.Check) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that adds one or more checks to the decorated :obj:`~.commands.base.CommandLike`
    object.

    Args:
        *cmd_checks (:obj:`~.checks.Check`): Check object(s) to add to the command.
    """

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        new_checks = [*c_like.checks, *cmd_checks]
        c_like.checks = new_checks
        return c_like

    return decorate
