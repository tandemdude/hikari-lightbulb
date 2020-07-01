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
import abc
import inspect
import typing


class Invokable(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def invoke(self, *args, **kwargs):
        ...

    def __get__(self, instance, owner):
        descriptor = _InvokableDescriptor(instance, self)
        instance.__dict__[self.name] = descriptor
        return descriptor


class _InvokableDescriptor(Invokable):
    def __init__(self, instance, invokable):
        self.__instance = instance
        self.__invokable = invokable

    @property
    def name(self):
        return

    def __getattr__(self, item):
        return getattr(self.__instance, item)

    def invoke(self, *args, **kwargs):
        return self.__invokable.invoke(self.__instance, *args, **kwargs)


class Command(Invokable):
    """
    A command that can be invoked by a user. When invoked, the callback
    will be called with a set argument ctx, an instance of the :obj:`.context.Context`
    class, and any other arguments supplied by the user.

    Args:
        callback: The coroutine to register as the command's callback.
        name (:obj:`str`): The name to register the command to.
    """

    def __init__(
        self,
        callback: typing.Callable,
        name: str,
        allow_extra_arguments: bool,
        aliases: typing.Iterable[str],
    ) -> None:
        self._callback = callback
        self._name = name
        self._allow_extra_arguments = allow_extra_arguments
        self._aliases = aliases
        self._checks = []
        self._pass_self = False

        signature = inspect.signature(callback)
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

    @property
    def name(self) -> str:
        """
        The registered name of the command

        Returns:
            :obj:`str`: Name of the command
        """
        return self._name

    def invoke(self, *args, **kwargs):
        """
        Invoke the command with given args and kwargs.

        Args:
            *args: The positional arguments to invoke the command with.

        Keyword Args:
            **kwargs: The keyword arguments to invoke the command with.

        """
        if self._pass_self:
            return self._callback(self, *args, **kwargs)
        return self._callback(*args, **kwargs)

    def add_check(self, check_func) -> None:
        """
        Add a check to an instance of :obj:`.commands.Command` or a subclass. The check passed must
        be an awaitable function taking a single argument which will be an instance of :obj:`.context.Context`.
        It must also either return a boolean denoting whether or not the check passed,
        or raise an instance of :obj:`.errors.CheckFailure` or a subclass.

        Args:
            check_func (Callable[ [ :obj:`.context.Context` ], Coroutine[ ``None``, ``None``, :obj:`bool` ] ]): Check to add to the command

        Returns:
            ``None``

        Example:

            .. code-block:: python

                async def author_name_startswith_foo(ctx):
                    return ctx.author.username.startswith("foo")

                bot.get_command("foo").add_check(author_name_startswith_foo)
        """
        self._checks.append(check_func)


class Group(Command):
    """
    A command group. This is invoked the same way as a normal command, however it has support
    for subcommands which can be registered to the group and invoked as separate commands.

    Args:
        *args: The args passed to :obj:`.commands.Command` in its constructor

    Keyword Args:
        **kwargs: The kwargs passed to :obj:`.commands.Command` in its constructor
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.subcommands = {}

    def _resolve_subcommand(
        self, args
    ) -> typing.Tuple[typing.Union[Command, Group], typing.Iterable[str]]:
        if len(args) == 1:
            return self, ()
        else:
            subcommand = self.subcommands.get(args[1])
            return (self, args[1:]) if subcommand is None else (subcommand, args[2:])

    def get_subcommand(self, name: str) -> Command:
        """
        Get a command object for a subcommand of the group from it's registered name.

        Args:
            name (:obj:`str`): The name of the command to get the object for.

        Returns:
            Optional[ :obj:`.commands.Command` ]: command object registered to that name.
        """
        return self.subcommands.get(name)

    def command(self, **kwargs):
        """
        A decorator that registers a callable as a subcommand for the command group.

        Keyword Args:
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (:obj:`str`): Optional name of the command. Defaults to the name of the function if not specified.
            aliases (Optional[ Iterable[ :obj:`str` ] ]): An iterable of aliases which can also invoke the command.

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
        subcommands = self.subcommands

        def decorate(func):
            nonlocal subcommands
            name = kwargs.get("name", func.__name__)
            subcommands[name] = Command(
                func,
                name,
                kwargs.get("allow_extra_arguments", True),
                kwargs.get("aliases", []),
            )
            for alias in kwargs.get("aliases", []):
                subcommands[alias] = subcommands[name]
            return subcommands[name]

        return decorate


def command(**kwargs):
    """
    A decorator to convert a coroutine into a :obj:`.commands.Command` object.

    Keyword Args:
        name (Optional[ :obj:`str` ]): Name to register the command to. Defaults to the name of the coroutine.
        allow_extra_arguments (Optional[ :obj:`bool` ]): Whether or not the command should error when run with
            more arguments than it takes. Defaults to True - will not raise an error.
        aliases (Iterable[ :obj:`str` ]): Iterable of aliases which will also invoke the command.
    """

    def decorate(func):
        name = kwargs.get("name", func.__name__)
        return Command(
            func,
            name,
            kwargs.get("allow_extra_arguments", True),
            kwargs.get("aliases", []),
        )

    return decorate


def group(**kwargs):
    """
    A decorator to convert a coroutine into a :obj:`.commands.Group` object.

    Keyword Args:
        name (Optional[ :obj:`str` ]): Name to register the command to. Defaults to the name of the coroutine.
        allow_extra_arguments (Optional[ :obj:`bool` ]): Whether or not the command should error when run with
            more arguments than it takes. Defaults to True - will not raise an error.
        aliases (Optional[ Iterable[ :obj:`str` ] ]): Iterable of aliases which will also invoke the command.
    """

    def decorate(func):
        name = kwargs.get("name", func.__name__)
        return Group(
            func,
            name,
            kwargs.get("allow_extra_arguments", True),
            kwargs.get("aliases", []),
        )

    return decorate
