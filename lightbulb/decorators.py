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

__all__ = ["implements", "command", "option", "add_checks", "set_help"]

import inspect
import typing as t

import hikari

from lightbulb import commands

if t.TYPE_CHECKING:
    from lightbulb import checks as checks_
    from lightbulb import context

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
        error_handler (Optional[ListenerT]): The function to register as the command's error handler. Defaults to
            ``None``. This can also be set with the :obj:`~.commands.base.CommandLike.set_error_handler`
            decorator.
        aliases (Sequence[:obj:`str`]): Aliases for the command. This will only affect prefix commands. Defaults
            to an empty list.
        guilds (Sequence[:obj:`int`]): The guilds that the command will be created in. This will only affect
            application commands. Defaults to an empty list.
        parser (:obj:`~.utils.parser.BaseParser`): The argument parser to use for prefix commands. Defaults
            to :obj:`~.utils.parser.Parser`.
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


def add_checks(*cmd_checks: checks_.Check) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
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


def set_help(
    text: t.Optional[t.Union[str, t.Callable[[commands.base.Command, context.base.Context], str]]] = None,
    *,
    docstring: bool = False,
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that defines the long help text for a command, or how the long help
    text should be retrieved. If ``text`` is provided then it will override the value for ``docstring``.

    Args:
        text (Union[Callable[[:obj:`~.commands.base.Command`, :obj:`~.context.base.Context`], :obj:`str`], :obj:`str`]): The
            long help text for the command, or a **syncronous** function called with the :obj:`~.commands.base.Command`
            object to get help text for and the :obj:`~.context.base.Context` that the help text should be
            retrieved for. If this is not provided, then you **must** pass the kwarg ``docstring=True``.

    Keyword Args:
        docstring (:obj:`bool`): Whether or not the command help text should be extracted from the command's docstring.
            If this is ``False`` (default) then a value **must** be provided for the ``text`` arg.
    """
    if text is None and docstring is False:
        raise ValueError("Either help text/callable or docstring=True must be provided")

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        if isinstance(text, str):
            getter = lambda _, __: text
        elif docstring:
            cmd_doc = inspect.getdoc(c_like.callback)
            if cmd_doc is None:
                raise ValueError("docstring=True was provided but the command does not have a docstring")
            getter = lambda _, __: cmd_doc  # type: ignore
        else:
            assert text is not None
            getter = text

        c_like.help_getter = getter
        return c_like

    return decorate
