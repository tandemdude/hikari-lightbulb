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
            from lightbulb import plugins, commands

            bot = lightbulb.Bot(token="token_here", prefix="!")

            class MyPlugin(plugins.Plugin):

                @commands.command()
                async def ping(self, ctx):
                    await ctx.send("Pong!")

            bot.add_plugin(MyPlugin())
    """

    def __init__(self, *, name: str = None) -> None:
        self.name = self.__class__.__name__ if name is None else name
        self.commands: typing.MutableMapping[
            str, typing.Union[commands.Command, commands.Group]
        ] = {}

        # we use type(self) since it will prevent the descriptor __get__ being
        # invoked to convert the command to a bound instance.
        for name, member in inspect.getmembers(type(self)):
            if isinstance(member, commands.Command):
                if not member.is_subcommand:
                    # using self here to now get the bound command.
                    self.commands[member.name] = getattr(self, name)
