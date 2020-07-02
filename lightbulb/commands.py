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
import inspect
import typing


_CommandT = typing.TypeVar("_CommandT", bound="Command")


class _BoundCommandMarker:
    def __init__(self, delegates_to: _CommandT) -> None:
        self.delegates_to = delegates_to


def _bind_prototype(instance: typing.Any, command_template: _CommandT):
    # Create a prototype of the command which is bound to the given instance.

    class BoundCommand(type(command_template), _BoundCommandMarker):
        def __init__(self) -> None:
            _BoundCommandMarker.__init__(self, command_template)
            # Do not init the super class, simply delegate to it using the __dict__
            self._delegates_to = command_template
            self.__dict__.update(command_template.__dict__.copy())

        def invoke(
            self, *args, **kwargs
        ) -> typing.Coroutine[None, typing.Any, typing.Any]:
            return self._callback(instance, *args, **kwargs)

    prototype = BoundCommand()

    # This will cache this for a later call!
    instance.__dict__[command_template.method_name] = prototype

    # Bind each subcommand to a descriptor for this specific instance.
    if isinstance(prototype, Group):
        prototype.subcommands = {}
        for subcommand_name, subcommand in command_template.subcommands.items():
            for name, member in inspect.getmembers(
                instance, lambda m: isinstance(m, _BoundCommandMarker)
            ):
                if member.delegates_to is subcommand:
                    # This will bind the instance to a bound method, and replace the parent. This completes the
                    # prototype, detatching it entirely from the class-bound implementation it was created from. This
                    # means adding the same plugin twice would attempt to add two unique copies of the command that
                    # hopefully are not aware of eachother by design, reducing weird side effects from shared attributes
                    # hopefully!
                    member.parent = prototype
                    prototype.subcommands[subcommand_name] = member

    return typing.cast(_CommandT, prototype)


class Command:
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
        parent: typing.Optional[typing.Any] = None,
    ) -> None:
        self._callback = callback
        self._name = name
        self._allow_extra_arguments = allow_extra_arguments
        self._aliases = aliases
        self._checks = []
        self.method_name: typing.Optional[str] = None
        self.parent = parent

        signature = inspect.signature(callback)
        self._has_max_args = not any(
            a.kind == inspect.Parameter.VAR_POSITIONAL
            for a in signature.parameters.values()
        )

        self._max_args: int = 0
        self._min_args: int = -1

        has_self = False

        for i, (name, param) in enumerate(signature.parameters.items()):
            if name == "self" and i == 0:
                has_self = True
                continue
            if param.default == inspect.Parameter.empty:
                self._min_args += 1

            # Skip the context, also skip counting self if it was present...
            if has_self and i > 1 or i > 0:
                self._max_args += 1

    def __get__(
        self: _CommandT, instance: typing.Any, owner: typing.Type[typing.Any]
    ) -> _CommandT:
        return _bind_prototype(instance, self)

    def __set_name__(self, owner, name):
        self.method_name = name

    @property
    def name(self) -> str:
        """
        The registered name of the command

        Returns:
            :obj:`str`: Name of the command
        """
        return self._name

    @property
    def is_subcommand(self) -> bool:
        """
        Returns:
            :obj:`True` if this object is a subcommand with a parent group,
            or :obj:`False` otherwise.
        """
        return self.parent is not None

    def invoke(self, *args, **kwargs):
        """
        Invoke the command with given args and kwargs.

        Args:
            *args: The positional arguments to invoke the command with.

        Keyword Args:
            **kwargs: The keyword arguments to invoke the command with.

        """
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
        this = self

        args.pop(0)

        while isinstance(this, Group) and args:
            try:
                this = this.subcommands[args[0]]
            except KeyError:
                break
            else:
                args = args[1:]

        return this, args

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
            cls = kwargs.pop("cls", Command)
            subcommands[name] = cls(
                func,
                name,
                kwargs.get("allow_extra_arguments", True),
                kwargs.get("aliases", []),
                parent=self,
            )
            for alias in kwargs.get("aliases", []):
                subcommands[alias] = subcommands[name]
            return subcommands[name]

        return decorate

    def group(self, **kwargs):
        kwargs["cls"] = type(self)
        return self.command(**kwargs)


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
