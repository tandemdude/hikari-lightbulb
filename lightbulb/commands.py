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

from lightbulb import context
from lightbulb import plugins


class Command:
    """
    A command that can be invoked by a user. When invoked, the :attr:`.commands.Command.callback` will be called
    with a set argument ``ctx``, and instance of the :class:`.context.Context` class, and any other arguments supplied
    by the user.

    Args:
        callable (:obj:`typing.Callable`): The callable object linked to the command.
        allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
        name (:obj:`str`): Optional name of the command. Defaults to the name of the function if not specified.
    """

    def __init__(
        self,
        callable: typing.Callable,
        allow_extra_arguments: bool,
        name: str,
        *,
        plugin: plugins.Plugin = None
    ) -> None:
        self.callback: typing.Callable = callable
        self.plugin: typing.Optional[plugins.Plugin] = plugin
        self.checks: typing.List[
            typing.Callable[[context.Context], typing.Coroutine[None, typing.Any, bool]]
        ] = []
        self.allow_extra_arguments: bool = allow_extra_arguments
        self.name: str = callable.__name__ if name is None else name
        self.help: typing.Optional[str] = inspect.getdoc(callable)

        signature = inspect.signature(callable)
        self._has_max_args: bool = (
            False
            if any(arg.kind == 2 for arg in signature.parameters.values())
            else True
        )

        self._max_args: int = len(signature.parameters) - 1
        self._min_args: int = -1
        for arg in signature.parameters.values():
            if arg.default == inspect.Parameter.empty:
                self._min_args += 1

    async def __call__(self, *args, **kwargs) -> None:
        await self.callback(*args)

    def add_check(
        self,
        check: typing.Callable[
            [context.Context], typing.Coroutine[None, typing.Any, bool]
        ],
    ) -> None:
        """
        Add a check to an instance of :obj:`.commands.Command`. The check passed must
        be an awaitable function taking a single argument which will be an instance of :obj:`.context.Context`.
        It must also either return a boolean denoting whether or not the check passed,
        or raise an instance of :obj:`.errors.CheckFailure` or a subclass.

        Args:
            check (Callable[ [ :obj:`.context.Context` ], Coroutine[ ``None``, ``None``, :obj:`bool` ] ]): Check to add to the command

        Returns:
            ``None``

        Example:

            .. code-block:: python

                async def author_name_startswith_foo(ctx):
                    return ctx.author.username.startswith("foo")

                bot.get_command("foo").add_check(author_name_startswith)
        """
        self.checks.append(check)


class Group(Command):
    """
    A command group. This is invoked the same way as a normal command, however it has support
    for subcommands which can be registered to the group and invoked as separate commands.

    Args:
        *args: The args passed to :obj:`.commands.Command` in its constructor
        **kwargs: The kwargs passed to :obj:`.commands.Command` in its constructor
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def command(
        self, *, allow_extra_arguments: bool = True, name: typing.Optional[str] = None
    ):
        """
        A decorator that registers a callable as a subcommand for the command group.

        Args:
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (:obj:`str`): Optional name of the command. Defaults to the name of the function if not specified.

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(token="token_here", prefix="!")

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
            nonlocal name
            name = func.__name__ if name is None else name
            if not registered_commands.get(name):
                registered_commands[name] = Command(func, allow_extra_arguments, name)
                return registered_commands[name]

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
