# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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
import typing
import inspect

from lightbulb import commands


def _is_command_partial(func):
    return hasattr(func, "__command_partial__")


def _get_command_partials(obj):
    for name, member in inspect.getmembers(obj, _is_command_partial):
        yield member, member.__command_partial__


def command(
    *, allow_extra_arguments: bool = True, name: typing.Optional[str] = None
) -> typing.Callable:
    """
    A decorator used to register a command to a plugin.

    Args:
        allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
            with more arguments than it requires. Defaults to True.
        name (Optional[ :obj:`str` ]): The name to register the command under.
    """

    def decorate(func):
        nonlocal allow_extra_arguments
        nonlocal name
        func.__command_partial__ = {
            "allow_extra_arguments": allow_extra_arguments,
            "name": name,
        }
        return func

    return decorate


class Plugin:
    """
    Independent class that can be loaded and unloaded from the bot
    to allow for hot-swapping of commands.

    To use in your own bot you should subclass this for each plugin
    you wish to create. Don't forget to cal ``super().__init__()`` if you
    override the ``__init__`` method.

    Args:
        name (Optional[ :obj:`str` ]): The name to register the plugin under. If unspecified will be the class name.

    Example:

        .. code-block:: python

            import lightbulb
            from lightbulb import plugins

            bot = lightbulb.Bot(token="token_here", prefix="!")

            class MyPlugin(plugins.Plugin):

                @plugins.command()
                async def ping(self, ctx):
                    await ctx.send("Pong!")

            bot.add_plugin(MyPlugin())
    """

    def __init__(self, *, name: str = None) -> None:
        self.name = self.__class__.__name__ if name is None else name
        self.commands: typing.MutableMapping[
            str, typing.Union[commands.Command, commands.Group]
        ] = {}

        for func, kwargs in _get_command_partials(self):
            self.add_command(func, **kwargs)

    def add_command(
        self,
        func,
        *,
        allow_extra_arguments: bool = True,
        name: typing.Optional[str] = None
    ) -> commands.Command:
        """
        Add a command to the plugin. This is an alternative to using the ``@plugins.command()`` decorator.

        Args:
            func: The function to register as a command.
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (Optional[ :obj:`str` ]): The name to register the command under.

        Returns:
            :obj:`.commands.Command`
        """
        name = func.__name__ if name is None else name
        if name not in self.commands:
            self.commands[name] = commands.Command(
                func, allow_extra_arguments, name, plugin=self
            )
            return self.commands[name]
