# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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

__all__: typing.Final[typing.List[str]] = [
    "SignatureInspector",
    "Command",
    "Group",
    "command",
    "group",
]

import functools
import inspect
import logging
import typing

import hikari
from multidict import CIMultiDict

from lightbulb import context as context_
from lightbulb import converters
from lightbulb import cooldowns
from lightbulb import errors
from lightbulb import events
from lightbulb.converters import _BaseConverter
from lightbulb.converters import _ConsumeRestConverter
from lightbulb.converters import _Converter
from lightbulb.converters import _DefaultingConverter
from lightbulb.converters import _GreedyConverter
from lightbulb.converters import _UnionConverter

if typing.TYPE_CHECKING:
    from lightbulb import plugins

_LOGGER = logging.getLogger("lightbulb")

_CommandT = typing.TypeVar("_CommandT", bound="Command")
T = typing.TypeVar("T")
_ConverterT = typing.Union[_BaseConverter[T], _BaseConverter[typing.List[T]]]

_CONVERTER_CLASS_MAPPING = {
    hikari.User: converters.user_converter,
    hikari.Member: converters.member_converter,
    hikari.TextableChannel: converters.text_channel_converter,
    hikari.GuildVoiceChannel: converters.guild_voice_channel_converter,
    hikari.GuildCategory: converters.category_converter,
    hikari.Role: converters.role_converter,
    hikari.Emoji: converters.emoji_converter,
    hikari.GuildPreview: converters.guild_converter,
    hikari.Message: converters.message_converter,
    hikari.Invite: converters.invite_converter,
    hikari.Colour: converters.colour_converter,
    hikari.Color: converters.colour_converter,
}


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
            self.__dict__.update(command_template.__dict__)

        def __hash__(self) -> int:
            return hash(self.name)

        def __eq__(self, other) -> bool:
            return isinstance(other, (type(self), Command)) and other.name == self.name

        async def invoke(self, context: context_.Context, *args: str, **kwargs: str) -> typing.Any:
            if self.cooldown_manager is not None:
                await self.cooldown_manager.add_cooldown(context)
            # Add the start slice on to the length to offset the section of arg_details being extracted

            return await self._callback(instance, context, *args, **kwargs)

    prototype = BoundCommand()

    # This will cache this for a later call!
    instance.__dict__[command_template.method_name] = prototype

    # Bind each subcommand to a descriptor for this specific instance.
    if isinstance(prototype, Group):
        prototype._subcommands = {}
        for subcommand_name, subcommand in command_template._subcommands.items():
            for name, member in inspect.getmembers(instance, lambda m: isinstance(m, _BoundCommandMarker)):
                if member.delegates_to is subcommand:
                    # This will bind the instance to a bound method, and replace the parent. This completes the
                    # prototype, detatching it entirely from the class-bound implementation it was created from. This
                    # means adding the same plugin twice would attempt to add two unique copies of the command that
                    # hopefully are not aware of eachother by design, reducing weird side effects from shared attributes
                    # hopefully!
                    member.parent = prototype
                    prototype._subcommands[subcommand_name] = member
                    prototype.subcommands.add(member)

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
        signature = inspect.signature(command._callback)
        self.converters = self.parse_signature(signature)
        self.arguments = [p.name for p in signature.parameters.values()]
        self.arguments.pop(0)
        if self.has_self:
            self.arguments.pop(0)

    def get_converter(self, annotation) -> _ConverterT:
        """
        Resolve the converter order for a given type annotation recursively.

        Args:
            annotation: The parameter's type annotation.

        Returns:
            The top level converter for the parameter
        """
        annotation = _CONVERTER_CLASS_MAPPING.get(annotation, annotation)
        if isinstance(annotation, str):
            annotation = str

        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)

        if origin is typing.Union:
            convs: typing.List[_ConverterT] = []

            for arg in args:
                if arg is None.__class__:
                    return _DefaultingConverter(_UnionConverter(*convs), None, raise_on_fail=False)

                convs.append(self.get_converter(arg))

            return _UnionConverter(*convs)

        if origin is converters.Greedy:
            return _GreedyConverter(self.get_converter(args[0]))

        return _Converter(annotation if annotation is not inspect.Parameter.empty else str)

    def parse_signature(self, signature: inspect.Signature):
        """
        Parse the command's callback signature into a list of the converters used
        for each command argument.

        Args:
            signature (:obj:`inspect.Signature`): The signature of the command callback.

        Returns:
            List of converters for command arguments in the correct order.
        """
        arg_converters = []

        for idx, param in enumerate(signature.parameters.values()):
            if idx == 0 or (idx == 1 and self.has_self):
                continue

            converter: _BaseConverter = self.get_converter(param.annotation)

            if param.kind is inspect.Parameter.KEYWORD_ONLY:
                converter = _ConsumeRestConverter(converter, param.name)
            elif param.kind is inspect.Parameter.VAR_POSITIONAL:
                converter = _GreedyConverter(converter, unpack=True)

            if param.default is not inspect.Parameter.empty:
                if not isinstance(converter, _DefaultingConverter):
                    converter = _DefaultingConverter(converter, param.default)
                else:
                    converter.default = param.default

            arg_converters.append(converter)
        return arg_converters


class Command:
    """
    A command that can be invoked by a user. When invoked, the callback
    will be called with a set argument ctx, an instance of the :obj:`~.context.Context`
    class, and any other arguments supplied by the user.

    Args:
        callback: The coroutine to register as the command's callback.
        name (:obj:`str`): The name to register the command to.
        allow_extra_arguments (:obj:`bool`): Whether or not the command should error
            when run with too many arguments.
        aliases (Iterable[ :obj:`str` ]): Additional names to register the command to.
        hidden (:obj:`bool`): Whether or not to show the command in the bot's help overview.
        parent (Optional[ :obj:`~Group` ]): The parent group for the command, or ``None`` if
            the command has no parent.
    """

    def __init__(
        self,
        callback: typing.Callable,
        name: str,
        allow_extra_arguments: bool,
        aliases: typing.Iterable[str],
        hidden: bool,
        parent: typing.Optional[typing.Any] = None,
    ) -> None:
        self._callback = callback
        self._name = name
        self._allow_extra_arguments = allow_extra_arguments
        self._aliases = aliases
        self.hidden = hidden
        self._checks = []
        self._check_exempt_predicate = lambda ctx: False
        self._raw_error_listener = None
        self._raw_before_invoke = None
        self._raw_after_invoke = None
        self.method_name: typing.Optional[str] = None
        self.parent: typing.Optional[Group] = parent
        """The parent group for the command. If ``None`` then the command is not a subcommand."""
        self.plugin: typing.Optional[plugins.Plugin] = None
        """The plugin the command is registered to. If ``None`` then it was defined outside of a plugin."""
        self.user_required_permissions: hikari.Permissions = hikari.Permissions.NONE
        """
        The permissions required by a user to run the command.
        These are extracted from the permission check decorator(s) on the command.
        """
        self.bot_required_permissions: hikari.Permissions = hikari.Permissions.NONE
        """
        The permissions the bot requires for a user to be able to run the command.
        These are extracted from the permission check decorator(s) on the command.
        """

        self.cooldown_manager: typing.Optional[cooldowns.CooldownManager] = None
        """The cooldown manager being used for the command. If ``None`` then the command does not have a cooldown."""

        signature = inspect.signature(callback)
        self._has_max_args = not any(
            a.kind == inspect.Parameter.VAR_POSITIONAL
            or a.kind == inspect.Parameter.KEYWORD_ONLY
            and a.default == inspect.Parameter.empty
            for a in signature.parameters.values()
        )

    def __get__(self: _CommandT, instance: typing.Any, owner: typing.Type[typing.Any]) -> _CommandT:
        return _bind_prototype(instance, self)

    def __set_name__(self, owner, name):
        self.method_name = name

    def __repr__(self) -> str:
        return f"<lightbulb.{self.__class__.__name__} {self.name} at {hex(id(self))}>"

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        return isinstance(other, type(self)) and other.name == self.name

    @functools.cached_property
    def _error_listener(self):
        if self.plugin is not None and self._raw_error_listener is not None:
            return getattr(self.plugin, self._raw_error_listener.__name__)
        return self._raw_error_listener

    @functools.cached_property
    def _before_invoke(self):
        if self.plugin is not None and self._raw_before_invoke is not None:
            return getattr(self.plugin, self._raw_before_invoke.__name__)
        return self._raw_before_invoke

    @functools.cached_property
    def _after_invoke(self):
        if self.plugin is not None and self._raw_after_invoke is not None:
            return getattr(self.plugin, self._raw_after_invoke.__name__)
        return self._raw_after_invoke

    @functools.cached_property
    def arg_details(self) -> SignatureInspector:
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
    def qualified_name(self) -> str:
        """
        The fully qualified name of the command, taking into account
        whether or not the command is a subcommand.

        Returns:
            :obj:`str`: Qualified name of the command.
        """
        command_qualname = []
        cmd = self
        while cmd is not None:
            command_qualname.append(cmd.name)
            cmd = cmd.parent
        return " ".join(command_qualname[::-1])

    @property
    def aliases(self) -> typing.Iterable[str]:
        """
        The command's aliases.

        Returns:
            Iterable[ :obj:`str` ]: Aliases for the command.
        """
        return self._aliases

    @property
    def is_subcommand(self) -> bool:
        """
        Whether or not the object is a subcommand with a parent group

        Returns:
            Union[ :obj:`True`, :obj:`False` ]: If this object is a subcommand with a parent group.
        """
        return self.parent is not None

    @property
    def callback(self) -> typing.Callable:
        """
        The command's callback coroutine

        Returns:
            Callable: The callback coroutine for the command
        """
        return self._callback

    @property
    def checks(self) -> typing.Iterable[typing.Callable[[context_.Context], bool]]:
        """
        The command's checks.

        Returns:
            Iterable[ Callable[ [ :obj:`~.context.Context` ], :obj:`bool` ] ]: The checks for the command.
        """
        return self._checks

    def command_error(self):
        """
        A decorator to register a coroutine as the command's error handler. Any return from the error handler
        will be used to determine whether or not the error was handled successfully. A return of any truthy
        object will prevent the event from propagating further down the listener chain. Returning a falsy value
        will mean that any global command error listener will then be called.

        The coroutine can only take one argument, which will be an instance of :obj:`~.events.CommandErrorEvent`
        unless in a class in which case it may also take the ``self`` argument.

        Example:

            .. code-block:: python

                @lightbulb.owner_only()
                @bot.command()
                async def foo(ctx):
                    await ctx.respond("bar")

                @foo.command_error()
                async def on_foo_error(event):
                    # This will be called if someone other than the
                    # bot's owner tries to run the command foo
                    return
        """

        def decorate(
            func: typing.Callable[[events.CommandErrorEvent], typing.Coroutine[None, None, typing.Any]]
        ) -> typing.Callable[[events.CommandErrorEvent], typing.Coroutine[None, None, typing.Any]]:
            self._raw_error_listener = func
            return func

        return decorate

    def before_invoke(self):
        """
        A decorator to register a coroutine to be run before the command is invoked.

        The coroutine can take only one argument which will be an instance of the :obj:`~.context.Context`
        for the command.
        """

        def decorate(
            func: typing.Callable[[context_.Context], typing.Coroutine[None, None, typing.Any]]
        ) -> typing.Callable[[context_.Context], typing.Coroutine[None, None, typing.Any]]:
            self._raw_before_invoke = func
            return func

        return decorate

    def after_invoke(self):
        """
        A decorator to register a coroutine to be run after the command is invoked.

        The coroutine can take only one argument which will be an instance of the :obj:`~.context.Context`
        for the command.
        """

        def decorate(
            func: typing.Callable[[context_.Context], typing.Coroutine[None, None, typing.Any]]
        ) -> typing.Callable[[context_.Context], typing.Coroutine[None, None, typing.Any]]:
            self._raw_after_invoke = func
            return func

        return decorate

    async def invoke(self, context: context_.Context, *args: str, **kwargs: str) -> typing.Any:
        """
        Invoke the command with given args and kwargs. Cooldowns and converters will
        be processed however this method bypasses all command checks.

        Args:
            context (:obj:`~.context.Context`): The command invocation context.
            *args: The positional arguments to invoke the command with.

        Keyword Args:
            **kwargs: The keyword arguments to invoke the command with.

        """
        if self.cooldown_manager is not None:
            await self.cooldown_manager.add_cooldown(context)

        return await self._callback(context, *args, **kwargs)

    def add_check(self, check_func: typing.Callable[[context_.Context], typing.Coroutine[None, None, bool]]) -> None:
        """
        Add a check to an instance of :obj:`~.commands.Command` or a subclass. The check passed must
        be an awaitable function taking a single argument which will be an instance of :obj:`~.context.Context`.
        It must also either return a boolean denoting whether or not the check passed,
        or raise an instance of :obj:`~.errors.CheckFailure` or a subclass.

        Args:
            check_func (Callable[ [ :obj:`~.context.Context` ], Coroutine[ ``None``, ``None``, :obj:`bool` ] ]): Check
                to add to the command

        Returns:
            ``None``

        Example:

            .. code-block:: python

                async def author_name_startswith_foo(ctx):
                    return ctx.author.username.startswith("foo")

                bot.get_command("foo").add_check(author_name_startswith_foo)

        See Also:
            :meth:`~.checks.check`
        """
        self._checks.append(check_func)

    async def is_runnable(self, context: context_.Context) -> bool:
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
            try:
                result = await check(context)
            except errors.MissingRequiredAttachment:
                # Bypass attachment check because we still want the command to show for the help
                # overview and it is unlikely that someone will call the help command with an attachment
                # to the message.
                result = True
            if result is False:
                raise errors.CheckFailure(f"Check {check.__name__} failed for command {self.name}")
        return True


class Group(Command):
    """
    A command group. This is invoked the same way as a normal command, however it has support
    for subcommands which can be registered to the group and invoked as separate commands.

    Args:
        *args: The args passed to :obj:`~.commands.Command` in its constructor

    Keyword Args:
        insensitive_commands (:obj:`bool`): Whether or not this group's subcommands should be case insensitive.
            Defaults to ``False``.
        inherit_checks (:obj:`bool`): Whether or not this group's subcommands should inherit the checks of the parent.
            Defaults to ``True``.
        **kwargs: The kwargs passed to :obj:`~.commands.Command` in its constructor
    """

    def __init__(self, *args, insensitive_commands: bool = False, inherit_checks: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.insensitive_commands = insensitive_commands
        self.inherit_checks = inherit_checks
        self._subcommands: typing.MutableMapping[str, Command] = {} if not self.insensitive_commands else CIMultiDict()
        self.subcommands: typing.Set[Command] = set()
        """A set containing all subcommands registered to the group."""

    def _resolve_subcommand(self, args) -> typing.Tuple[typing.Union[Command, Group], typing.Iterable[str]]:
        this = self

        args.pop(0)
        while isinstance(this, Group) and args:
            invoked_with = args[0].casefold() if this.insensitive_commands else args[0]
            try:
                this = this._subcommands[invoked_with]
            except KeyError:
                break
            else:
                args = args[1:]

        return this, args

    def walk_commands(self) -> typing.Generator[Command, None, None]:
        """
        A generator that walks through all commands and subcommands registered to this group.

        Yields:
            :obj:`~.commands.Command`: All commands, groups and subcommands registered to this group.
        """
        for command in self.subcommands:
            yield command
            if isinstance(command, Group):
                yield from command.walk_commands()

    def add_check(self, check_func: typing.Callable[[context_.Context], typing.Coroutine[None, None, bool]]) -> None:
        if self.inherit_checks:
            for c in self.subcommands:
                c.add_check(check_func)
        super().add_check(check_func)

    def get_subcommand(self, name: str) -> Command:
        """
        Get a command object for a subcommand of the group from it's registered name.

        Args:
            name (:obj:`str`): The name of the command to get the object for.

        Returns:
            Optional[ :obj:`~.commands.Command` ]: command object registered to that name.
        """
        return self._subcommands.get(name)

    def command(self, **kwargs):
        """
        A decorator that registers a callable as a subcommand for the command group.

        Keyword Args:
            **kwargs: Kwargs passed to :obj:`~command`

        Example:

            .. code-block:: python

                bot = lightbulb.Bot(token="token_here", prefix="!")

                @bot.group()
                async def foo(ctx):
                    await ctx.respond("Invoked foo")

                @foo.command()
                async def bar(ctx):
                    await ctx.respond("Invoked foo bar")
        """

        def decorate(func):
            name = kwargs.get("name", func.__name__)
            cls = kwargs.get("cls", Command)
            self._subcommands[name] = cls(
                func,
                name,
                kwargs.get("allow_extra_arguments", True),
                kwargs.get("aliases", []),
                kwargs.get("hidden", False),
                parent=self,
            )
            if self.inherit_checks:
                self._subcommands[name]._checks.extend(self._checks)
            self.subcommands.add(self._subcommands[name])
            for alias in kwargs.get("aliases", []):
                self._subcommands[alias] = self._subcommands[name]
            return self._subcommands[name]

        return decorate

    def group(self, **kwargs):
        """
        A decorator that registers a callable as a subgroup for the command group.

        Keyword Args:
            **kwargs: Kwargs passed to :obj:`~group`
        """
        kwargs["cls"] = type(self)

        def decorate(func):
            name = kwargs.get("name", func.__name__)
            cls = kwargs.get("cls", Group)
            self._subcommands[name] = cls(
                func,
                name,
                kwargs.get("allow_extra_arguments", True),
                kwargs.get("aliases", []),
                kwargs.get("hidden", False),
                insensitive_commands=kwargs.get("insensitive_commands", False),
                inherit_checks=kwargs.get("inherit_checks", True),
                parent=self,
            )
            if self.inherit_checks:
                self._subcommands[name]._checks.extend(self._checks)
            self.subcommands.add(self._subcommands[name])
            for alias in kwargs.get("aliases", []):
                self._subcommands[alias] = self._subcommands[name]
            return self._subcommands[name]

        return decorate


def command(**kwargs):
    """
    A decorator to convert a coroutine into a :obj:`~.commands.Command` object.

    Keyword Args:
        name (Optional[ :obj:`str` ]): Name to register the command to. Defaults to the name of the coroutine.
        allow_extra_arguments (Optional[ :obj:`bool` ]): Whether or not the command should error when run with
            more arguments than it takes. Defaults to True - will not raise an error.
        aliases (Iterable[ :obj:`str` ]): Iterable of aliases which will also invoke the command.
        hidden (:obj:`bool`): Whether or not the command should be hidden from the help command. Defaults to ``False``.
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
            kwargs.get("hidden", False),
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
        hidden (:obj:`bool`): Whether or not the command should be hidden from the help command. Defaults to ``False``.
        insensitive_commands (:obj:`bool`): Whether or not subcommands should be case-insensitive. Defaults to
            False.
        cls (:obj:`~.commands.Command`): The class to use to instantiate the group object from. Defaults
            to :obj:`~.commands.Group`.
        inherit_checks (:obj:`bool`): Whether or not subcommands should inherit checks added to the base group.
    """

    def decorate(func):
        name = kwargs.get("name", func.__name__)
        cls = kwargs.get("cls", Group)
        return cls(
            func,
            name,
            kwargs.get("allow_extra_arguments", True),
            kwargs.get("aliases", []),
            kwargs.get("hidden", False),
            insensitive_commands=kwargs.get("insensitive_commands", False),
            inherit_checks=kwargs.get("inherit_checks", True),
        )

    return decorate
