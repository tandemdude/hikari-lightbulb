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
import functools
from multidict import CIMultiDict

from lightbulb import context
from lightbulb import errors


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


class SignatureInspector:
    """
    Contains information about the arguments that a command takes when
    it is invoked.

    Args:
        command (:obj:`~.commands.Command`): The command to inspect the arguments of.
    """

    def __init__(self, command: Command) -> None:
        self.command = command
        self.has_self = isinstance(command, _BoundCommandMarker)
        self.args = {}
        for index, (name, arg) in enumerate(
            inspect.signature(command._callback).parameters.items()
        ):
            self.args[name] = self.parse_arg(index, arg)
        self.max_args = sum(not arg["ignore"] for arg in self.args.values())
        self.min_args = sum(
            not arg["ignore"] and arg["required"] for arg in self.args.values()
        )
        self.has_max_args = not any(
            a.kind == inspect.Parameter.VAR_POSITIONAL
            or (a.kind == inspect.Parameter.KEYWORD_ONLY and a.default is a.empty)
            for a in inspect.signature(command._callback).parameters.values()
        )

    def parse_arg(self, index, arg):
        details = {}
        if index == 0:
            details["ignore"] = True
        elif index == 1 and self.has_self:
            details["ignore"] = True
        else:
            details["ignore"] = False

        details["argtype"] = arg.kind
        details["annotation"] = arg.annotation
        details["required"] = (arg.default is arg.empty) or (
            arg.kind == 3
        )  # var positional
        return details

    def _args_and_name_before_asterisk(self):
        args_num = 0
        param_name = None

        for idx, arg in enumerate(self.args.values()):

            if arg["argtype"] == inspect.Parameter.KEYWORD_ONLY and arg["required"]:
                args_num = idx
                param_name = list(self.args.keys())[idx]
                break

            # If last arg is *arg, -1 from args_num to concatenate inputs correctly
            if (
                idx + 1 == len(self.args)
                and arg["argtype"] == inspect.Parameter.VAR_POSITIONAL
            ):
                args_num -= 1

        # args_num will be 0 when it didn't encounter any *arg or *, arg
        # args_num will be -1 when it didn't encounter any *, arg but found *arg at the end
        if args_num in (0, -1):
            args_num += len(self.args)

        # Check if number or *, args is bigger than 1 and throw error if yes
        if len(self.args) - args_num > 1:
            raise TypeError(
                f"Number of arguments after * (asterisk) symbol in command {self.command._callback.__name__} has to be smaller or equal 1."
            )

        args_num -= 1  # because of the ctx arg

        if self.has_self:
            args_num -= 1  # because of the self arg if exists
        return args_num, param_name


class Command:
    """
    A command that can be invoked by a user. When invoked, the callback
    will be called with a set argument ctx, an instance of the :obj:`~.context.Context`
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
            or a.kind == inspect.Parameter.KEYWORD_ONLY
            and a.default == inspect.Parameter.empty
            for a in signature.parameters.values()
        )

    def __get__(
        self: _CommandT, instance: typing.Any, owner: typing.Type[typing.Any]
    ) -> _CommandT:
        return _bind_prototype(instance, self)

    def __set_name__(self, owner, name):
        self.method_name = name

    @functools.cached_property
    def arg_details(self):
        """
        An inspection of the arguments that a command takes.

        Returns:
            :obj:`~.commands.SignatureInspector`: Details about the command's arguments.
        """
        return SignatureInspector(self)

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
        Whether or not the object is a subcommand with a parent group

        Returns:
            Union[ :obj:`True`, :obj:`False` ]: If this object is a subcommand with a parent group.
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
        Add a check to an instance of :obj:`~.commands.Command` or a subclass. The check passed must
        be an awaitable function taking a single argument which will be an instance of :obj:`~.context.Context`.
        It must also either return a boolean denoting whether or not the check passed,
        or raise an instance of :obj:`~.errors.CheckFailure` or a subclass.

        Args:
            check_func (Callable[ [ :obj:`~.context.Context` ], Coroutine[ ``None``, ``None``, :obj:`bool` ] ]): Check to add to the command

        Returns:
            ``None``

        Example:

            .. code-block:: python

                async def author_name_startswith_foo(ctx):
                    return ctx.author.username.startswith("foo")

                bot.get_command("foo").add_check(author_name_startswith_foo)
        """
        self._checks.append(check_func)

    async def is_runnable(self, context: context.Context) -> bool:
        """
        Run all the checks for the command to determine whether or not it is
        runnable in the given context.

        Args:
            context (:obj:`~.context.Context`): The context to evaluate the checks with.

        Returns:
            :obj:`bool`: If the command is runnable in the context given.

        Raises:
            :obj:`~.errors.CheckFailure`: If the command is not runnable in the context given.
        """
        for check in self._checks:
            result = await check(context)
            if result is False:
                raise errors.CheckFailure(
                    f"Check {check.__name__} failed for command {self.name}"
                )
        return True


class Group(Command):
    """
    A command group. This is invoked the same way as a normal command, however it has support
    for subcommands which can be registered to the group and invoked as separate commands.

    Args:
        *args: The args passed to :obj:`~.commands.Command` in its constructor

    Keyword Args:
        insensitive_commands (:obj:`bool`): Whether or not this group's subcommands should be case insensitive. Defaults to ``False``.
        **kwargs: The kwargs passed to :obj:`~.commands.Command` in its constructor
    """

    def __init__(self, *args, insensitive_commands: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.insensitive_commands = insensitive_commands
        self.subcommands = {} if not self.insensitive_commands else CIMultiDict()

    def _resolve_subcommand(
        self, args
    ) -> typing.Tuple[typing.Union[Command, Group], typing.Iterable[str]]:
        this = self

        args.pop(0)
        while isinstance(this, Group) and args:
            invoked_with = args[0].casefold() if this.insensitive_commands else args[0]
            try:
                this = this.subcommands[invoked_with]
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
            Optional[ :obj:`~.commands.Command` ]: command object registered to that name.
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
            cls = kwargs.get("cls", Command)
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
        """
        A decorator that registers a callable as a subgroup for the command group.

        Keyword Args:
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if the command is run
                with more arguments than it requires. Defaults to True.
            name (:obj:`str`): Optional name of the command. Defaults to the name of the function if not specified.
            aliases (Optional[ Iterable[ :obj:`str` ] ]): An iterable of aliases which can also invoke the command.
        """
        kwargs["cls"] = type(self)
        return self.command(**kwargs)


def command(**kwargs):
    """
    A decorator to convert a coroutine into a :obj:`~.commands.Command` object.

    Keyword Args:
        name (Optional[ :obj:`str` ]): Name to register the command to. Defaults to the name of the coroutine.
        allow_extra_arguments (Optional[ :obj:`bool` ]): Whether or not the command should error when run with
            more arguments than it takes. Defaults to True - will not raise an error.
        aliases (Iterable[ :obj:`str` ]): Iterable of aliases which will also invoke the command.
        cls (:obj:`~.commands.Command`): The class to use to instantiate the command object from. Defaults
            to :obj:`~.commands.Command`.
    """

    def decorate(func):
        name = kwargs.get("name", func.__name__)
        cls = kwargs.get("cls", Command)
        return cls(
            func,
            name,
            kwargs.get("allow_extra_arguments", True),
            kwargs.get("aliases", []),
        )

    return decorate


def group(**kwargs):
    """
    A decorator to convert a coroutine into a :obj:`~.commands.Group` object.

    Keyword Args:
        name (Optional[ :obj:`str` ]): Name to register the command to. Defaults to the name of the coroutine.
        allow_extra_arguments (Optional[ :obj:`bool` ]): Whether or not the command should error when run with
            more arguments than it takes. Defaults to True - will not raise an error.
        aliases (Optional[ Iterable[ :obj:`str` ] ]): Iterable of aliases which will also invoke the command.
        cls (:obj:`~.commands.Command`): The class to use to instantiate the group object from. Defaults
            to :obj:`~.commands.Group`.
    """

    def decorate(func):
        name = kwargs.get("name", func.__name__)
        cls = kwargs.get("cls", Group)
        return cls(
            func,
            name,
            kwargs.get("allow_extra_arguments", True),
            kwargs.get("aliases", []),
            insensitive_commands=kwargs.get("insensitive_commands", False),
        )

    return decorate
