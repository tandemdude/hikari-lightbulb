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
    "OptionData",
    "Option",
    "string",
    "integer",
    "boolean",
    "number",
    "user",
    "channel",
    "role",
    "mentionable",
    "attachment",
]

import dataclasses
import typing as t

import hikari

from lightbulb import di
from lightbulb import utils
from lightbulb.commands import utils as cmd_utils
from lightbulb.internal.utils import non_undefined_or

if t.TYPE_CHECKING:
    from lightbulb import commands
    from lightbulb import context
    from lightbulb import localization

    AutocompleteProvider = t.Callable[[context.AutocompleteContext[context.T]], t.Awaitable[t.Any]]

T = t.TypeVar("T")
D = t.TypeVar("D")
CtxMenuOptionReturnT = t.Union[hikari.User, hikari.Message]


@dataclasses.dataclass(slots=True, frozen=True)
class Choice(t.Generic[T]):
    name: str
    """The name of the choice."""
    value: T
    """The value of the choice."""
    localize: bool = False
    """Whether the name of the choice should be interpreted as a localization key."""


@dataclasses.dataclass(slots=True)
class OptionData(t.Generic[D]):
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

    default: hikari.UndefinedOr[D] = hikari.UNDEFINED
    """The default value for the option."""
    choices: hikari.UndefinedOr[t.Sequence[Choice[t.Any]]] = hikari.UNDEFINED
    """The choices for the option."""
    channel_types: hikari.UndefinedOr[t.Sequence[hikari.ChannelType]] = hikari.UNDEFINED
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
    """The provider to use to resolve autocomplete interactions for this command."""

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
        name_localizations: t.Mapping[hikari.Locale, str] = {}
        description_localizations: t.Mapping[hikari.Locale, str] = {}

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


class Option(t.Generic[T, D]):
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

    def __init__(self, data: OptionData[D], default_when_not_bound: T) -> None:
        self._data = data
        self._unbound_default = default_when_not_bound

    def __get__(self, instance: commands.CommandBase | None, owner: type[commands.CommandBase]) -> T | D:
        if instance is None or getattr(instance, "_current_context", None) is None:
            return self._unbound_default

        return instance._resolve_option(self)


class ContextMenuOption(Option[CtxMenuOptionReturnT, CtxMenuOptionReturnT]):
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

    def __init__(self, type_: type[CtxMenuOptionReturnT]) -> None:
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

    def __get__(self, instance: commands.CommandBase | None, owner: type[commands.CommandBase]) -> CtxMenuOptionReturnT:
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


def string(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[t.Sequence[Choice[str]]] = hikari.UNDEFINED,
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[str]] = hikari.UNDEFINED,
) -> str | D:
    """
    A string option.

    Args:
        name: The name of the option.
        description: The description of the option.
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
    """
    return t.cast(
        str,
        Option(
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
            ),
            utils.EMPTY,
        ),
    )


def integer(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[t.Sequence[Choice[int]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[int]] = hikari.UNDEFINED,
) -> int | D:
    """
    An integer option.

    Args:
        name: The name of the option.
        description: The description of the option.
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
    """
    return t.cast(
        int,
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
            ),
            utils.EMPTY,
        ),
    )


def boolean(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> bool | D:
    """
    A boolean option.

    Args:
        name: The name of the option.
        description: The description of the option.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    return t.cast(
        bool,
        Option(
            OptionData(
                type=hikari.OptionType.BOOLEAN,
                name=name,
                description=description,
                localize=localize,
                default=default,
            ),
            utils.EMPTY,
        ),
    )


def number(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[t.Sequence[Choice[float]]] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProvider[float]] = hikari.UNDEFINED,
) -> float | D:
    """
    A numeric (float) option.

    Args:
        name: The name of the option.
        description: The description of the option.
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
    """
    return t.cast(
        float,
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
            ),
            utils.EMPTY,
        ),
    )


def user(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.User | D:
    """
    A user option.

    Args:
        name: The name of the option.
        description: The description of the option.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    return t.cast(
        hikari.User,
        Option(
            OptionData(
                type=hikari.OptionType.USER,
                name=name,
                description=description,
                localize=localize,
                default=default,
            ),
            utils.EMPTY,
        ),
    )


def channel(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    channel_types: hikari.UndefinedOr[t.Sequence[hikari.ChannelType]] = hikari.UNDEFINED,
) -> hikari.PartialChannel | D:
    """
    A channel option.

    Args:
        name: The name of the option.
        description: The description of the option.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.
        channel_types: The channel types permitted for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    return t.cast(
        hikari.PartialChannel,
        Option(
            OptionData(
                type=hikari.OptionType.CHANNEL,
                name=name,
                description=description,
                localize=localize,
                default=default,
                channel_types=channel_types,
            ),
            utils.EMPTY,
        ),
    )


def role(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Role | D:
    """
    A role option.

    Args:
        name: The name of the option.
        description: The description of the option.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    return t.cast(
        hikari.Role,
        Option(
            OptionData(
                type=hikari.OptionType.ROLE,
                name=name,
                description=description,
                localize=localize,
                default=default,
            ),
            utils.EMPTY,
        ),
    )


def mentionable(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Snowflake | D:
    """
    A mentionable (snowflake) option.

    Args:
        name: The name of the option.
        description: The description of the option.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    return t.cast(
        hikari.Snowflake,
        Option(
            OptionData(
                type=hikari.OptionType.MENTIONABLE,
                name=name,
                description=description,
                localize=localize,
                default=default,
            ),
            utils.EMPTY,
        ),
    )


def attachment(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Attachment | D:
    """
    An attachment option.

    Args:
        name: The name of the option.
        description: The description of the option.
        localize: Whether to localize this option's name and description. If :obj:`True`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default: The default value for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    return t.cast(
        hikari.Attachment,
        Option(
            OptionData(
                type=hikari.OptionType.MENTIONABLE,
                name=name,
                description=description,
                localize=localize,
                default=default,
            ),
            utils.EMPTY,
        ),
    )
