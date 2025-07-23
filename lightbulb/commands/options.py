# -*- coding: utf-8 -*-
# Copyright (c) 2023-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

__all__ = [
    "Choice",
    "Option",
    "OptionData",
    "attachment",
    "boolean",
    "channel",
    "integer",
    "mentionable",
    "number",
    "role",
    "string",
    "user",
]

import dataclasses
import typing as t

import hikari

from lightbulb import di
from lightbulb import utils
from lightbulb.commands import utils as cmd_utils
from lightbulb.internal.utils import non_undefined_or

if t.TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence

    from lightbulb import commands
    from lightbulb import context
    from lightbulb import localization
    from lightbulb.internal import types

    AutocompleteProvider = Callable[[context.AutocompleteContext[context.T]], Awaitable[t.Any]]

T = t.TypeVar("T")

DefaultT = t.TypeVar("DefaultT")
ConvertedT = t.TypeVar("ConvertedT")

CtxMenuOptionReturn: t.TypeAlias = t.Union[hikari.User, hikari.Message]


@dataclasses.dataclass(slots=True, frozen=True)
class Choice(t.Generic[T]):
    name: str
    """The name of the choice."""
    value: T
    """The value of the choice."""
    localize: bool = False
    """Whether the name of the choice should be interpreted as a localization key."""


@dataclasses.dataclass(slots=True)
class OptionData(t.Generic[DefaultT, ConvertedT]):
    """
    Dataclass for storing information about an option necessary for command creation.

    This should generally not be instantiated manually. An appropriate one will be generated when defining
    an option within a command class.
    """

    type: hikari.OptionType
    """The type of the option."""
    name: str
    """The name of the option."""
    description: str
    """The description of the option."""
    localize: bool = False
    """Whether the name and description of the option should be interpreted as localization keys."""

    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED
    """The default value for the option."""
    choices: hikari.UndefinedOr[Sequence[Choice[t.Any]]] = hikari.UNDEFINED
    """The choices for the option."""
    channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]] = hikari.UNDEFINED
    """The channel types for the option."""

    min_value: hikari.UndefinedOr[int | float] = hikari.UNDEFINED
    """The minimum value for the option."""
    max_value: hikari.UndefinedOr[int | float] = hikari.UNDEFINED
    """The maximum value for the option."""

    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED
    """The minimum length for the option."""
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED
    """The maximum length for the option."""

    autocomplete: bool = False
    """Whether autocomplete is enabled for the option."""
    autocomplete_provider: hikari.UndefinedOr[AutocompleteProvider[t.Any]] = hikari.UNDEFINED
    """The provider to use to resolve autocomplete interactions for this option."""

    converter: t.Callable[[context.Context, t.Any], ConvertedT] | None = None
    """
    The converter to use for this option.

    .. versionadded:: 3.1.0
    """

    _localized_name: str = dataclasses.field(init=False, default="")
    _localized_description: str = dataclasses.field(init=False, default="")

    def __post_init__(self) -> None:
        if not self.localize and (len(self.name) < 1 or len(self.name) > 32):
            raise ValueError("'name' - must be 1-32 characters")
        if not self.localize and (len(self.description) < 1 or len(self.description) > 100):
            raise ValueError("'description' - must be 1-100 characters")

        if self.choices is not hikari.UNDEFINED:
            if len(self.choices) > 25:
                raise ValueError("'choices' - cannot have more than 25 choices")

            for i, choice in enumerate(self.choices):
                if not choice.localize and (len(choice.name) < 1 or len(choice.name) > 100):
                    raise ValueError(f"'choices[{i}]' - name must be 1-100 characters")
                if isinstance(choice.value, str) and len(choice.value) > 100:
                    raise ValueError(f"'choices[{i}]' - value must be <= 100 characters")

        if self.type is hikari.OptionType.STRING:
            if self.min_length is not hikari.UNDEFINED and (self.min_length < 0 or self.min_length > 6000):
                raise ValueError("'min_length' - must be between 0 and 6000 (inclusive)")
            if self.max_length is not hikari.UNDEFINED and (self.max_length < 1 or self.max_length > 6000):
                raise ValueError("'max_length' - must be between 1 and 6000 (inclusive)")

        if self.autocomplete_provider is not hikari.UNDEFINED:
            self.autocomplete_provider = di.with_di(self.autocomplete_provider)

    async def to_command_option(
        self, default_locale: hikari.Locale, localization_provider: localization.LocalizationProvider
    ) -> hikari.CommandOption:
        """
        Convert this option data into a hikari :obj:`~hikari.commands.CommandOption`.

        Args:
            default_locale: The default locale to use when resolving localizations.
            localization_provider: The localization provider to use when resolving localizations.

        Returns:
            The created command option.
        """
        name, description = self.name, self.description
        name_localizations: Mapping[hikari.Locale, str] = {}
        description_localizations: Mapping[hikari.Locale, str] = {}

        if self.localize:
            (
                name,
                description,
                name_localizations,
                description_localizations,
            ) = await cmd_utils.localize_name_and_description(name, description, default_locale, localization_provider)

        self._localized_name = name
        self._localized_description = description

        choices: list[hikari.CommandChoice] = []
        if self.choices is not hikari.UNDEFINED:
            for choice in self.choices:
                if not choice.localize:
                    choices.append(hikari.CommandChoice(name=choice.name, value=choice.value))
                    continue

                c_name, c_localizations = await cmd_utils.localize_value(
                    choice.name, default_locale, localization_provider
                )
                choices.append(
                    hikari.CommandChoice(name=c_name, name_localizations=c_localizations, value=choice.value)  # type: ignore[reportArgumentType]
                )

        return hikari.CommandOption(
            type=self.type,
            name=name,
            name_localizations=name_localizations,  # type: ignore[reportArgumentType]
            description=description,
            description_localizations=description_localizations,  # type: ignore[reportArgumentType]
            is_required=self.default is hikari.UNDEFINED,
            choices=choices or None,
            channel_types=self.channel_types or None,
            min_value=non_undefined_or(self.min_value, None),
            max_value=non_undefined_or(self.max_value, None),
            min_length=self.min_length if self.min_length is not hikari.UNDEFINED else None,
            max_length=self.max_length if self.max_length is not hikari.UNDEFINED else None,
            autocomplete=self.autocomplete,
        )


class Option(t.Generic[DefaultT, ConvertedT]):
    """
    Descriptor class representing a command option.

    This class should generally not be instantiated manually and instead be created through the
    use of one of the helper functions.

    Args:
        data: The dataclass describing this instance.
        default_when_not_bound: The value to return from the descriptor if accessed through the class
            instead of through an instance

    See Also:
        :meth:`~string`
        :meth:`~integer`
        :meth:`~boolean`
        :meth:`~number`
        :meth:`~user`
        :meth:`~channel`
        :meth:`~role`
        :meth:`~mentionable`
        :meth:`~attachment`
    """

    __slots__ = ("_data", "_unbound_default")

    def __init__(
        self,
        data: OptionData[DefaultT, ConvertedT],
        default_when_not_bound: DefaultT,
    ) -> None:
        self._data = data
        self._unbound_default = default_when_not_bound

    def __get__(
        self, instance: commands.CommandBase | None, owner: type[commands.CommandBase]
    ) -> DefaultT | ConvertedT:
        if instance is None or getattr(instance, "_current_context", None) is None:
            return self._unbound_default

        if self._data._localized_name not in instance._resolved_option_cache:
            raise RuntimeError(f"Tried to access option {self._data._localized_name} before resolving options.")

        return t.cast("DefaultT", instance._resolved_option_cache[self._data._localized_name])


class ContextMenuOption(Option[CtxMenuOptionReturn, CtxMenuOptionReturn]):
    """
    Special implementation of :obj:`~Option` to handle context menu command targets given that
    they do not count as an "option" and the ID is instead given through the ``target`` field on the
    interaction.

    Args:
        type: The type of the context menu command. Either ``hikari.User`` or ``hikari.Message``.

    Warning:
        You should never have to instantiate this yourself. When subclassing one of the context menu command
        classes, a ``target`` option will be inherited automatically.
    """

    __slots__ = ("_type",)

    def __init__(self, type_: type[CtxMenuOptionReturn]) -> None:
        self._type = type_
        super().__init__(
            OptionData(
                type=hikari.OptionType.STRING,
                name="target",
                description="target",
            ),
            utils.EMPTY,
        )

    @t.overload
    def __get__(self, instance: commands.UserCommand | None, owner: type[commands.UserCommand]) -> hikari.User: ...

    @t.overload
    def __get__(
        self, instance: commands.MessageCommand | None, owner: type[commands.MessageCommand]
    ) -> hikari.Message: ...

    def __get__(self, instance: commands.CommandBase | None, owner: type[commands.CommandBase]) -> CtxMenuOptionReturn:
        if instance is None or getattr(instance, "_current_context", None) is None:
            return self._unbound_default

        assert instance._current_context is not None
        interaction = instance._current_context.interaction
        resolved = interaction.resolved

        assert resolved is not None
        assert interaction.target_id is not None
        if self._type is hikari.User:
            user = resolved.members.get(interaction.target_id) or resolved.users.get(interaction.target_id)
            assert isinstance(user, hikari.User)
            return user

        message = resolved.messages.get(interaction.target_id)
        assert isinstance(message, hikari.Message)
        return message


@t.overload
def string(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[str]]] = hikari.UNDEFINED,
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[str]] = hikari.UNDEFINED,
) -> str | DefaultT: ...


@t.overload
def string(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, str], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[str]]] = hikari.UNDEFINED,
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[str]] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def string(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, str], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[str]]] = hikari.UNDEFINED,
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[str]] = hikari.UNDEFINED,
) -> str | DefaultT | ConvertedT:
    """
    A string option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.
        choices: The choices for the option.
        min_length: The minimum length for the option.
        max_length: The maximum length for the option.
        autocomplete: The autocomplete provider function to use for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    opt = Option(
        OptionData(
            type=hikari.OptionType.STRING,
            name=name,
            description=description,
            localize=localize,
            default=default,
            choices=choices,
            min_length=min_length,
            max_length=max_length,
            autocomplete=autocomplete is not hikari.UNDEFINED,
            autocomplete_provider=autocomplete,
            converter=converter,
        ),
        utils.EMPTY,
    )
    return t.cast("str", opt)


@t.overload
def integer(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[int]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[int]] = hikari.UNDEFINED,
) -> int | DefaultT: ...


@t.overload
def integer(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, int], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[int]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[int]] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def integer(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, int], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[int]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[int]] = hikari.UNDEFINED,
) -> int | DefaultT | ConvertedT:
    """
    An integer option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.
        choices: The choices for the option.
        min_value: The minimum value for the option.
        max_value: The maximum value for the option.
        autocomplete: The autocomplete provider function to use for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "int",
        Option(
            OptionData(
                type=hikari.OptionType.INTEGER,
                name=name,
                description=description,
                localize=localize,
                default=default,
                choices=choices,
                min_value=min_value,
                max_value=max_value,
                autocomplete=autocomplete is not hikari.UNDEFINED,
                autocomplete_provider=autocomplete,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )


@t.overload
def boolean(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> bool | DefaultT: ...


@t.overload
def boolean(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, bool], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def boolean(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, bool], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> bool | DefaultT | ConvertedT:
    """
    A boolean option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "bool",
        Option(
            OptionData(
                type=hikari.OptionType.BOOLEAN,
                name=name,
                description=description,
                localize=localize,
                default=default,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )


@t.overload
def number(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[float]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[float]] = hikari.UNDEFINED,
) -> float | DefaultT: ...


@t.overload
def number(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, float], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[float]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[float]] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def number(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, float], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[Sequence[Choice[float]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[float]] = hikari.UNDEFINED,
) -> float | DefaultT | ConvertedT:
    """
    A numeric (float) option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.
        choices: The choices for the option.
        min_value: The minimum value for the option.
        max_value: The maximum value for the option.
        autocomplete: The autocomplete provider function to use for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "float",
        Option(
            OptionData(
                type=hikari.OptionType.FLOAT,
                name=name,
                description=description,
                localize=localize,
                default=default,
                choices=choices,
                min_value=min_value,
                max_value=max_value,
                autocomplete=autocomplete is not hikari.UNDEFINED,
                autocomplete_provider=autocomplete,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )


@t.overload
def user(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.User | DefaultT: ...


@t.overload
def user(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.User], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def user(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.User], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.User | DefaultT | ConvertedT:
    """
    A user option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "hikari.User",
        Option(
            OptionData(
                type=hikari.OptionType.USER,
                name=name,
                description=description,
                localize=localize,
                default=default,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )


@t.overload
def channel(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]] = hikari.UNDEFINED,
) -> hikari.PartialChannel | DefaultT: ...


@t.overload
def channel(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.PartialChannel], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def channel(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.PartialChannel], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
    channel_types: hikari.UndefinedOr[Sequence[hikari.ChannelType]] = hikari.UNDEFINED,
) -> hikari.PartialChannel | DefaultT | ConvertedT:
    """
    A channel option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.
        channel_types: The channel types permitted for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "hikari.PartialChannel",
        Option(
            OptionData(
                type=hikari.OptionType.CHANNEL,
                name=name,
                description=description,
                localize=localize,
                default=default,
                channel_types=channel_types,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )


@t.overload
def role(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.Role | DefaultT: ...


@t.overload
def role(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.Role], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def role(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.Role], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.Role | DefaultT | ConvertedT:
    """
    A role option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "hikari.Role",
        Option(
            OptionData(
                type=hikari.OptionType.ROLE,
                name=name,
                description=description,
                localize=localize,
                default=default,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )


@t.overload
def mentionable(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.Snowflake | DefaultT: ...


@t.overload
def mentionable(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.Snowflake], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def mentionable(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.Snowflake], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.Snowflake | DefaultT | ConvertedT:
    """
    A mentionable (snowflake) option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "hikari.Snowflake",
        Option(
            OptionData(
                type=hikari.OptionType.MENTIONABLE,
                name=name,
                description=description,
                localize=localize,
                default=default,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )


@t.overload
def attachment(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.Attachment | DefaultT: ...


@t.overload
def attachment(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.Attachment], types.MaybeAwaitable[ConvertedT]],
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> DefaultT | ConvertedT: ...


def attachment(
    name: str,
    description: str,
    /,
    *,
    converter: t.Callable[[context.Context, hikari.Attachment], types.MaybeAwaitable[ConvertedT]] | None = None,
    localize: bool = False,
    default: hikari.UndefinedOr[DefaultT] = hikari.UNDEFINED,
) -> hikari.Attachment | DefaultT | ConvertedT:
    """
    An attachment option.

    Args:
        name: The name of the option.
        description: The description of the option.
        converter: The converter to be used to convert the value to a custom type.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.

    .. versionadded:: 3.1.0
        The ``converter`` argument.
    """
    return t.cast(
        "hikari.Attachment",
        Option(
            OptionData(
                type=hikari.OptionType.ATTACHMENT,
                name=name,
                description=description,
                localize=localize,
                default=default,
                converter=converter,
            ),
            utils.EMPTY,
        ),
    )
