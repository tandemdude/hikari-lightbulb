# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
#
# This file is part of Hikari Command Handler.
#
# Hikari Command Handler is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari Command Handler is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari Command Handler. If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations
import typing
import inspect


class Command:
    """
    A command that can be invoked by a user. When invoked, the :attr:`.commands.Command.callback` will be called
    with a set argument ``ctx``, and instance of the :class:`.context.Context` class, and any other arguments supplied
    by the user.

    Args:
        callable (:obj:`typing.Callable`): The callable object linked to the command.
    """

    def __init__(self, callable: typing.Callable, allow_extra_arguments: bool) -> None:
        self.callback = callable
        self.allow_extra_arguments = allow_extra_arguments
        self.name = callable.__name__
        self.help: typing.Optional[str] = inspect.getdoc(callable)
        signature = inspect.signature(callable)
        self._has_max_args = (
            False
            if any(arg.kind == 2 for arg in signature.parameters.values())
            else True
        )
        self._max_args = len(signature.parameters) - 1
        self._min_args = -1
        for arg in signature.parameters.values():
            if arg.default == inspect.Parameter.empty:
                self._min_args += 1

    async def __call__(self, *args, **kwargs) -> None:
        await self.callback(*args)


class Group(Command):
    """
    A command group. This is invoked the same way as a normal command, however it has support
    for subcommands which can be registered to the group and invoked as separate commands.

    Args:
        *args: The args passed to :obj:`.commands.Command` in its constructor
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.subcommands: typing.MutableMapping[str, Command] = {}

    def resolve_subcommand(
        self, args: typing.List[str]
    ) -> typing.Tuple[typing.Union[Command, Group], typing.List[str]]:
        """
        Resolve the subcommand that should be called from the list of arguments provided. If
        not subcommand is found it returns itself to be invoked instead.

        Args:
            args (List[ :obj:`str` ]): Arguments to resolve subcommand from

        Returns:
            Tuple[ Union[ :obj:`.commands.Command`, :obj:`.commands.Group` ], List[ :obj:`str` ] ] Containing the command
            to be invoked, followed by a list of the arguments for the command to be invoked with.
        """
        if len(args) == 1:
            return (self, args[1:])
        else:
            subcommand = self.subcommands.get(args[1])
            return (
                (subcommand, args[2:]) if subcommand is not None else (self, args[1:])
            )

    def command(self, allow_extra_arguments=True):
        """
        A decorator that registers a callable as a subcommand for the command group.

        Args:
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if a command is run
                with more arguments than it requires. Defaults to True.

        Example:

            .. code-block:: python

                bot = handler.Bot(token="token_here", prefix="!")

                @bot.group()
                async def foo(ctx):
                    await ctx.reply("Invoked foo")

                @foo.command()
                async def bar(ctx):
                    await ctx.reply("Invoked foo bar")
        """
        registered_commands = self.subcommands

        def decorate(func: typing.Callable):
            nonlocal registered_commands
            nonlocal allow_extra_arguments
            if not registered_commands.get(func.__name__):
                registered_commands[func.__name__] = Command(
                    func, allow_extra_arguments
                )
                return registered_commands[func.__name__]

        return decorate

    def get_subcommand(self, name: str) -> typing.Optional[Command]:
        """
        Get a command object for a subcommand of the group from it's registered name.

        Args:
            name (:obj:`str`): The name of the command to get the object for.

        Returns:
            Optional[ :obj:`.commands.Command` ] command object registered to that name.
        """
        return self.subcommands.get(name)
