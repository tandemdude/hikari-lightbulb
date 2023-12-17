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

__all__ = [
    "implements",
    "command",
    "option",
    "add_checks",
    "check_exempt",
    "add_cooldown",
    "set_help",
    "set_max_concurrency",
    "app_command_permissions",
]

import functools
import inspect
import typing as t

import hikari

from lightbulb import buckets
from lightbulb import checks as checks_
from lightbulb import commands
from lightbulb import cooldown_algorithms
from lightbulb import cooldowns

if t.TYPE_CHECKING:
    from lightbulb import context

T = t.TypeVar("T")
CommandCallbackT = t.TypeVar("CommandCallbackT", bound=t.Callable[..., t.Coroutine[t.Any, t.Any, None]])
AutocompleteCallbackT = t.Callable[
    [hikari.CommandInteractionOption, hikari.AutocompleteInteraction],
    t.Coroutine[
        t.Any,
        t.Any,
        t.Union[
            str, hikari.api.AutocompleteChoiceBuilder, t.Sequence[t.Union[str, hikari.api.AutocompleteChoiceBuilder]]
        ],
    ],
]


def implements(
    *command_types: t.Type[commands.base.Command],
) -> t.Callable[[CommandCallbackT], CommandCallbackT]:
    """
    Second order decorator that defines the command types that a given callback function will implement.

    Args:
        *command_types (Type[:obj:`~.commands.base.Command`]): Command types that the function will implement.
    """

    def decorate(func: CommandCallbackT) -> CommandCallbackT:
        setattr(func, "__cmd_types__", command_types)
        return func

    return decorate


def command(  # noqa: D417 (undocumented-param)
    name: str, description: str, *, cls: t.Type[commands.base.CommandLike] = commands.base.CommandLike, **kwargs: t.Any
) -> t.Callable[[CommandCallbackT], commands.base.CommandLike]:
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
        auto_defer (:obj:`bool`): Whether to automatically defer the response when the command is invoked. If
            ``True``, the bot will send an initial response of type ``DEFERRED_MESSAGE_CREATE`` for interactions, and
            for prefix commands, typing will be triggered in the invocation channel.
        ephemeral (:obj:`bool`): Whether to send responses from the invocation of this command as ephemeral by
            default. If ``True`` then all responses from the command will use the flag :obj:`hikari.MessageFlags.EPHEMERAL`.
            This will not affect prefix commands as responses from prefix commands **cannot** be ephemeral.
        hidden (:obj:`bool`): Whether to hide the command from the help command. Defaults to ``False``.
        inherit_checks (:obj:`bool`): Whether or not the command should inherit checks from the parent group. Only
            affects subcommands. Defaults to ``False``.
        pass_options (:obj:`bool`): Whether the command will have its options passed as keyword arguments when invoked.
        name_localizations (Mapping[Union[:obj:`hikari.locales.Locale`, :obj:`str`], :obj:`str`]): A mapping of
            locale to name localizations for this command. Defaults to an empty dictionary.
        description_localizations (Mapping[Union[:obj:`hikari.locales.Locale`, :obj:`str`], :obj:`str`]): A mapping
            of locale to description localizations for this command. Defaults to an empty dictionary.
        nsfw (:obj:`bool`): Whether the command should only be enabled in NSFW channels. For prefix commands, this
            will add an NSFW-channel only check to the command automatically. For slash commands, this will behave
            as specified in the Discord documentation.
        cls (Type[:obj:`~.commands.base.CommandLike`]): ``CommandLike`` class to instantiate from this decorator.
            Defaults to :obj:`~.commands.base.CommandLike`.

    .. versionadded:: 2.1.0
        ``cls`` kwarg.
    .. versionadded:: 2.2.1
        ``pass_options`` kwarg.
    .. versionadded:: 2.3.0
        ``name_localizations`` and ``description_localizations`` kwargs.
    """  # noqa: E501 (line-too-long)

    def decorate(func: CommandCallbackT) -> commands.base.CommandLike:
        cmd = cls(func, name, description, **kwargs)
        if cmd.nsfw:
            # Add nsfw channel check only for prefix commands. For other command types the check will just return True
            add_checks(checks_.Check(checks_._nsfw_channel_only, lambda ctx: True, lambda ctx: True, lambda ctx: True))(
                cmd
            )
        return cmd

    return decorate


def option(  # noqa: D417 (undocumented-param)
    name: str,
    description: str,
    type: t.Any = str,
    *,
    required: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    choices: t.Optional[t.Sequence[t.Union[str, int, float, hikari.CommandChoice]]] = None,
    channel_types: t.Optional[t.Sequence[hikari.ChannelType]] = None,
    default: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED,
    modifier: commands.base.OptionModifier = commands.base.OptionModifier.NONE,
    min_value: t.Optional[t.Union[int, float]] = None,
    max_value: t.Optional[t.Union[int, float]] = None,
    min_length: t.Optional[int] = None,
    max_length: t.Optional[int] = None,
    autocomplete: t.Union[bool, AutocompleteCallbackT] = False,
    cls: t.Type[commands.base.OptionLike] = commands.base.OptionLike,
    **kwargs: t.Any,
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that adds an option to the decorated :obj:`~.commands.base.CommandLike`
    object.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        type (Any): The type of the option. This will be used as the converter for prefix commands.

    Keyword Args:
        required (UndefinedOr[:obj:`bool`]): Whether this option is required. This will be inferred from whether a
            default value for the option was specified if not otherwise specified.
        choices (Optional[Sequence[Union[:obj:`str`, :obj:`int`, :obj:`float`, :obj:`~hikari.commands.CommandChoice`]]]): The
            choices for the option. This will only affect slash commands. Defaults to ``None``.
        channel_types (Optional[Sequence[hikari.channels.ChannelType]]): The channel types allowed for the option.
            This will only affect slash commands. Defaults to ``None``.
        default (UndefinedOr[Any]): The default value for the option. Defaults to :obj:`~hikari.undefined.UNDEFINED`.
        modifier (:obj:`~.commands.base.OptionModifier`): Modifier controlling how the option should be parsed. Defaults
            to ``OptionModifier.NONE``.
        min_value (Optional[Union[:obj:`float`, :obj:`int`]]): The minimum value permitted for this option (inclusive).
            Only available if the option type is numeric (integer or float). Defaults to ``None``.
        max_value (Optional[Union[:obj:`float`, :obj:`int`]]): The maximum value permitted for this option (inclusive).
            Only available if the option type is numeric (integer or float). Defaults to ``None``.
        min_length (Optional[:obj:`int`]): The minimum length permitted for this option. Only available if this option
            is string type.
        max_length (Optional[:obj:`int`]): The maximum length permitted for this option. Only available if this option
            is string type.
        autocomplete (Union[:obj:`bool`, AutocompleteCallbackT]): Boolean representing whether the option will use
            autocomplete or the callback to use for autocomplete for this option. This will only affect slash commands.
            Defaults to ``False``.
        name_localizations (Mapping[Union[:obj:`hikari.locales.Locale`, :obj:`str`], :obj:`str`]): A mapping of locale
            to name localizations for this option. Defaults to an empty dictionary.
        description_localizations (Mapping[Union[:obj:`hikari.locales.Locale`, :obj:`str`], :obj:`str`]): A mapping of
            locale to description localizations for this option. Defaults to an empty dictionary.
        cls (Type[:obj:`~.commands.base.OptionLike`]): ``OptionLike`` class to instantiate from this decorator. Defaults
            to :obj:`~.commands.base.OptionLike`.

    .. versionadded:: 2.1.0
        ``cls`` kwarg.
    .. versionadded:: 2.1.3
        ``min_value`` and ``max_value`` kwargs.
    .. versionadded:: 2.3.2
        ``min_length`` and ``max_length`` kwargs.
    """  # noqa: E501 (line-too-long)

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        nonlocal default, required, autocomplete

        if not isinstance(c_like, commands.base.CommandLike):
            raise SyntaxError("'option' decorator must be above the 'command' decorator")

        required = required if required is not hikari.UNDEFINED else (default is hikari.UNDEFINED)
        assert isinstance(required, bool)
        if not required:
            default = None if default is hikari.UNDEFINED else default

        if not isinstance(autocomplete, bool):
            c_like._autocomplete_callbacks[name] = autocomplete
            autocomplete = True

        c_like.options[name] = cls(
            name=name,
            description=description,
            arg_type=type,
            required=required,
            choices=choices,
            channel_types=channel_types,
            default=default,
            modifier=modifier,
            min_value=min_value,
            max_value=max_value,
            min_length=min_length,
            max_length=max_length,
            autocomplete=autocomplete,
            **kwargs,
        )
        return c_like

    return decorate


def add_checks(
    *cmd_checks: t.Union[checks_.Check, checks_._ExclusiveCheck],
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that adds one or more checks to the decorated :obj:`~.commands.base.CommandLike`
    object.

    Args:
        *cmd_checks (:obj:`~.checks.Check`): Check object(s) to add to the command.
    """

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        if not isinstance(c_like, commands.base.CommandLike):
            raise SyntaxError("'add_checks' decorator must be above the 'command' decorator")

        new_checks = [*c_like.checks, *cmd_checks]
        c_like.checks = new_checks

        for check in cmd_checks:
            check.add_to_object_hook(c_like)

        return c_like

    return decorate


def check_exempt(
    predicate: t.Callable[[context.base.Context], t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]],
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator which allows all checks to be bypassed if the ``predicate`` conditions are met.
    Predicate can be a synchronous or asynchronous function but must take a single argument - ``context`` - and
    must return  a boolean - ``True`` if checks should be bypassed or ``False`` if not.

    Args:
        predicate (Callable[[:obj:`~.context.base.Context`], Union[:obj:`bool`, Coroutine[Any, Any, :obj:`bool`]]): The
            function to call to check if the checks should be bypassed for the given context.
    """

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        if not isinstance(c_like, commands.base.CommandLike):
            raise SyntaxError("'check_exempt' decorator must be above the 'command' decorator")

        c_like.check_exempt = predicate
        return c_like

    return decorate


@t.overload
def add_cooldown(
    length: float,
    uses: int,
    bucket: t.Type[buckets.Bucket],
    algorithm: t.Type[cooldown_algorithms.CooldownAlgorithm] = cooldown_algorithms.BangBangCooldownAlgorithm,
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    ...


@t.overload
def add_cooldown(
    *,
    callback: t.Callable[[context.base.Context], t.Union[buckets.Bucket, t.Coroutine[t.Any, t.Any, buckets.Bucket]]],
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    ...


def add_cooldown(
    length: t.Optional[float] = None,
    uses: t.Optional[int] = None,
    bucket: t.Optional[t.Type[buckets.Bucket]] = None,
    algorithm: t.Type[cooldown_algorithms.CooldownAlgorithm] = cooldown_algorithms.BangBangCooldownAlgorithm,
    *,
    callback: t.Optional[
        t.Callable[[context.base.Context], t.Union[buckets.Bucket, t.Coroutine[t.Any, t.Any, buckets.Bucket]]]
    ] = None,
    cls: t.Type[cooldowns.CooldownManager] = cooldowns.CooldownManager,
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that sets the cooldown manager for a command.

    Args:
        length (:obj:`float`): The length in seconds of the cooldown timer.
        uses (:obj:`int`): The number of command invocations before the cooldown will be triggered.
        bucket (Type[:obj:`~.buckets.Bucket`]): The bucket to use for cooldowns.
        algorithm (Type[:obj:`~.cooldown_algorithms.CooldownAlgorithm`]): The cooldown algorithm to use. Defaults
            to :obj:`~.cooldown_algorithms.BangBangCooldownAlgorithm`.

    Keyword Args:
        callback (Callable[[:obj:`~.context.base.Context`], Union[:obj:`~.buckets.Bucket`, Coroutine[Any, Any, :obj:`~.buckets.Bucket`]]]): Callable
            that takes the context the command was invoked under and returns the appropriate bucket object to use for
            cooldowns in the context.
        cls (Type[:obj:`~.cooldowns.CooldownManager`]): The cooldown manager class to use. Defaults to
            :obj:`~.cooldowns.CooldownManager`.
    """  # noqa: E501 (line-too-long)
    getter: t.Callable[[context.base.Context], t.Union[buckets.Bucket, t.Coroutine[t.Any, t.Any, buckets.Bucket]]]
    if length is not None and uses is not None and bucket is not None:

        def _get_bucket(
            ctx: context.base.Context,
            _bucket: t.Type[buckets.Bucket],
            _length: float,
            _uses: int,
            _algorithm: t.Type[cooldown_algorithms.CooldownAlgorithm],
        ) -> buckets.Bucket:
            return _bucket(_length, _uses, _algorithm)

        getter = functools.partial(_get_bucket, _bucket=bucket, _length=length, _uses=uses, _algorithm=algorithm)
    elif callback is not None:
        getter = callback
    else:
        raise TypeError("Invalid arguments - either provided all of the args length,uses,bucket or the kwarg callback")

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        if not isinstance(c_like, commands.base.CommandLike):
            raise SyntaxError("'add_cooldown' decorator must be above the 'command' decorator")

        c_like.cooldown_manager = cls(getter)
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
            long help text for the command, or a **synchronous** function called with the :obj:`~.commands.base.Command`
            object to get help text for and the :obj:`~.context.base.Context` that the help text should be
            retrieved for. If this is not provided, then you **must** pass the kwarg ``docstring=True``.

    Keyword Args:
        docstring (:obj:`bool`): Whether the command help text should be extracted from the command's docstring.
            If this is ``False`` (default) then a value **must** be provided for the ``text`` arg.
    """  # noqa: E501 (line-too-long)
    if text is None and docstring is False:
        raise ValueError("Either help text/callable or docstring=True must be provided")

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        if not isinstance(c_like, commands.base.CommandLike):
            raise SyntaxError("'set_help' decorator must be above the 'command' decorator")

        if isinstance(text, str):
            getter = lambda _, __: text  # noqa: E731 (lambda-assignment)
        elif docstring:
            cmd_doc = inspect.getdoc(c_like.callback)
            if cmd_doc is None:
                raise ValueError("docstring=True was provided but the command does not have a docstring")
            getter = lambda _, __: cmd_doc  # noqa: E731 (lambda-assignment)
        else:
            assert text is not None
            getter = text

        c_like.help_getter = getter
        return c_like

    return decorate


def set_max_concurrency(
    uses: int, bucket: t.Type[buckets.Bucket]
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that defines the max concurrency limit for a command.

    Args:
        uses (:obj:`int`): The maximum number of uses of the command that can be executing
            concurrently before a :obj:`~.errors.MaxConcurrencyLimitReached` will be raised upon invocation.
        bucket (Type[:obj:`~.buckets.Bucket`]): Bucket that command max concurrency will be processed under.

    .. versionadded:: 2.2.1
    """
    if uses < 1 or not isinstance(uses, int):
        raise ValueError("'uses' must be a positive integer")

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        if not isinstance(c_like, commands.base.CommandLike):
            raise SyntaxError("'set_max_concurrency' decorator must be above the 'command' decorator")
        c_like.max_concurrency = (uses, bucket)

        return c_like

    return decorate


def app_command_permissions(
    perms: t.Optional[hikari.Permissions] = None, *, dm_enabled: bool = True, bypass_checks: bool = False
) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
    """
    Second order decorator that defines the application command permissions v2 configuration
    for a command.

    Args:
        perms (Optional[:obj:`hikari.Permissions`]): The permissions to set as the default for the command when
            it is created in a guild. If ``None``, no default permissions will be set.
        dm_enabled (:obj:`bool`): Whether the command should be available in DM. If the command is not global
            then this will have no effect.
        bypass_checks (:obj:`bool`): Whether author permissions checks will be bypassed when this command is
            invoked as an application command. This allows guild admins to dictate who is allowed to use the command
            as opposed to enforcing a set of permissions.

    .. versionadded:: 2.2.3
    """

    def decorate(c_like: commands.base.CommandLike) -> commands.base.CommandLike:
        if perms is not None:
            c_like.app_command_default_member_permissions = perms

        c_like.app_command_dm_enabled = dm_enabled
        c_like.app_command_bypass_author_permission_checks = bypass_checks

        return c_like

    return decorate
