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

import collections.abc
import dataclasses
import typing as t

import hikari

from lightbulb import utils
from lightbulb.commands import utils as cmd_utils

if t.TYPE_CHECKING:
    from lightbulb import commands
    from lightbulb import context
    from lightbulb import localization

    AutocompleteProviderT = t.Callable[[context.AutocompleteContext], t.Awaitable[t.Any]]  # TODO

T = t.TypeVar("T")
D = t.TypeVar("D")
CtxMenuOptionReturnT = t.Union[hikari.User, hikari.Message]


def _non_undefined_or(item: hikari.UndefinedOr[T], default: D) -> t.Union[T, D]:
    return item if item is not hikari.UNDEFINED else default


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
    choices: hikari.UndefinedOr[t.Sequence[hikari.CommandChoice]] = hikari.UNDEFINED
    """The choices for the option."""
    channel_types: hikari.UndefinedOr[t.Sequence[hikari.ChannelType]] = hikari.UNDEFINED
    """The channel types for the option."""

    min_value: hikari.UndefinedOr[t.Union[int, float]] = hikari.UNDEFINED
    """The minimum value for the option."""
    max_value: hikari.UndefinedOr[t.Union[int, float]] = hikari.UNDEFINED
    """The maximum value for the option."""

    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED
    """The minimum length for the option."""
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED
    """The maximum length for the option."""

    autocomplete: bool = False
    """Whether autocomplete is enabled for the option."""
    autocomplete_provider: hikari.UndefinedOr[AutocompleteProviderT] = hikari.UNDEFINED

    def __post_init__(self) -> None:
        if len(self.name) < 1 or len(self.name) > 32:
            raise ValueError("'name' - must be 1-32 characters")
        if len(self.description) < 1 or len(self.description) > 100:
            raise ValueError("'description' - must be 1-100 characters")

        if self.choices is not hikari.UNDEFINED:
            if len(self.choices) > 25:
                raise ValueError("'choices' - cannot have more than 25 choices")

            for i, choice in enumerate(self.choices):
                if len(choice.name) < 1 or len(choice.name) > 100:
                    raise ValueError(f"'choices[{i}]' - name must be 1-100 characters")
                if isinstance(choice.value, str) and len(choice.value) > 100:
                    raise ValueError(f"'choices[{i}]' - value must be <= 100 characters")

        if self.type is hikari.OptionType.STRING:
            if self.min_length is not hikari.UNDEFINED and (self.min_length < 0 or self.min_length > 6000):
                raise ValueError("'min_length' - must be between 0 and 6000 (inclusive)")
            if self.max_length is not hikari.UNDEFINED and (self.max_length < 1 or self.max_length > 6000):
                raise ValueError("'max_length' - must be between 1 and 6000 (inclusive)")

    def to_command_option(
        self, default_locale: hikari.Locale, localization_provider: localization.LocalizationProviderT
    ) -> hikari.CommandOption:
        name, description = self.name, self.description
        name_localizations: t.Mapping[hikari.Locale, str] = {}
        description_localizations: t.Mapping[hikari.Locale, str] = {}

        if self.localize:
            name, description, name_localizations, description_localizations = cmd_utils.localize_name_and_description(
                name, description, default_locale, localization_provider
            )

        return hikari.CommandOption(
            type=self.type,
            name=name,
            name_localizations=name_localizations,  # type: ignore[reportArgumentType]
            description=description,
            description_localizations=description_localizations,  # type: ignore[reportArgumentType]
            is_required=self.default is not hikari.UNDEFINED,
            choices=_non_undefined_or(self.choices, None),
            channel_types=_non_undefined_or(self.channel_types, None),
            min_value=_non_undefined_or(self.min_value, None),
            max_value=_non_undefined_or(self.max_value, None),
            min_length=_non_undefined_or(self.min_length, None),
            max_length=_non_undefined_or(self.max_length, None),
            autocomplete=self.autocomplete,
        )


class Option(t.Generic[T, D]):
    """
    Descriptor class representing a command option.

    This class should generally not be instantiated manually and instead be created through the
    use of one of the helper functions.

    Args:
        data (:obj:`~OptionData` [ ``D`` ]): The dataclass describing this instance.
        default_when_not_bound (``T``): The value to return from the descriptor if accessed through the class
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

    __slots__ = ("_data", "_unbound_default", "_supports_autocomplete")

    def __init__(self, data: OptionData[D], default_when_not_bound: T) -> None:
        self._data = data
        self._unbound_default = default_when_not_bound

    def __get__(self, instance: t.Optional[commands.CommandBase], owner: t.Type[commands.CommandBase]) -> t.Union[T, D]:
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

    def __init__(self, type: t.Type[CtxMenuOptionReturnT]) -> None:
        self._type = type
        super().__init__(
            OptionData(
                type=hikari.OptionType.STRING,
                name="target",
                description="target",
            ),
            utils.EMPTY_USER if type is hikari.User else utils.EMPTY_MESSAGE,
        )

    @t.overload
    def __get__(
        self, instance: t.Optional[commands.UserCommand], owner: t.Type[commands.UserCommand]
    ) -> hikari.User: ...

    @t.overload
    def __get__(
        self, instance: t.Optional[commands.MessageCommand], owner: t.Type[commands.MessageCommand]
    ) -> hikari.Message: ...

    def __get__(
        self, instance: t.Optional[commands.CommandBase], owner: t.Type[commands.CommandBase]
    ) -> CtxMenuOptionReturnT:
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


# TODO - consider how to implement choice localisation
def _normalise_choices(
    choices: t.Union[
        t.Sequence[hikari.CommandChoice],
        t.Mapping[str, t.Union[str, int, float]],
        t.Sequence[t.Tuple[str, t.Union[str, int, float]]],
        t.Sequence[t.Union[str, int, float]],
    ],
) -> t.Sequence[hikari.CommandChoice]:
    if isinstance(choices, collections.abc.Mapping):
        return [hikari.CommandChoice(name=k, value=v) for k, v in choices.items()]

    def _to_command_choice(
        item: t.Union[
            hikari.CommandChoice,
            t.Tuple[str, t.Union[str, int, float]],
            str,
            int,
            float,
        ],
    ) -> hikari.CommandChoice:
        if isinstance(item, hikari.CommandChoice):
            return item

        if isinstance(item, (str, int, float)):
            return hikari.CommandChoice(name=str(item), value=item)

        return hikari.CommandChoice(name=item[0], value=item[1])

    return list(map(_to_command_choice, choices))


def string(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[
        t.Union[t.Sequence[hikari.CommandChoice], t.Mapping[str, str], t.Sequence[t.Tuple[str, str]], t.Sequence[str]]
    ] = hikari.UNDEFINED,
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProviderT] = hikari.UNDEFINED,
) -> str:
    """
    A string option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.
        choices (:obj:`~hikari.undefined.UndefinedOr` [ ``ChoicesT`` ]): The choices for the option. Any of the
            following can be interpreted as a choice: a sequence of :obj:`~hikari.commands.CommandChoice`, a mapping
            of choice name to choice value, a sequence of 2-tuples where the first element is the name
            and the second element is the value, or a sequence of :obj:`str` where the choice name and value will
            be the same.
        min_length (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The minimum length for the option.
        max_length (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The maximum length for the option.
        autocomplete: The autocomplete provider function to use for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    if choices is not hikari.UNDEFINED:
        choices = _normalise_choices(choices)

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
            "",
        ),
    )


def integer(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[
        t.Union[t.Sequence[hikari.CommandChoice], t.Mapping[str, int], t.Sequence[t.Tuple[str, int]], t.Sequence[int]]
    ] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProviderT] = hikari.UNDEFINED,
) -> int:
    """
    An integer option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.
        choices (:obj:`~hikari.undefined.UndefinedOr` [ ``ChoicesT`` ]): The choices for the option. Any of the
            following can be interpreted as a choice: a sequence of :obj:`~hikari.commands.CommandChoice`, a mapping
            of choice name to choice value, a sequence of 2-tuples where the first element is the name
            and the second element is the value, or a sequence of :obj:`int` where the choice name and value will
            be the same.
        min_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The minimum value for the option.
        max_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The maximum value for the option.
        autocomplete: The autocomplete provider function to use for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    if choices is not hikari.UNDEFINED:
        choices = _normalise_choices(choices)

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
            0,
        ),
    )


def boolean(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> bool:
    """
    A boolean option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.

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
            False,
        ),
    )


def number(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: hikari.UndefinedOr[
        t.Union[
            t.Sequence[hikari.CommandChoice], t.Mapping[str, float], t.Sequence[t.Tuple[str, float]], t.Sequence[float]
        ]
    ] = hikari.UNDEFINED,
    min_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    autocomplete: hikari.UndefinedOr[AutocompleteProviderT] = hikari.UNDEFINED,
) -> float:
    """
    A numeric (float) option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.
        choices (:obj:`~hikari.undefined.UndefinedOr` [ ``ChoicesT`` ]): The choices for the option. Any of the
            following can be interpreted as a choice: a sequence of :obj:`~hikari.commands.CommandChoice`, a mapping
            of choice name to choice value, a sequence of 2-tuples where the first element is the name
            and the second element is the value, or a sequence of :obj:`float` where the choice name and value will
            be the same.
        min_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`float` ]): The minimum value for the option.
        max_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`float` ]): The maximum value for the option.
        autocomplete: The autocomplete provider function to use for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """
    if choices is not hikari.UNDEFINED:
        choices = _normalise_choices(choices)

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
            0.0,
        ),
    )


def user(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.User:
    """
    A user option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.

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
            utils.EMPTY_USER,
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
) -> hikari.PartialChannel:
    """
    A channel option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.
        channel_types (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`~typing.Sequence` [ :obj:`~hikari.channels.ChannelType` ]]): The
            channel types permitted for the option.

    Returns:
        Descriptor allowing access to the option value from within a command invocation.
    """  # noqa: E501
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
            default_when_not_bound=utils.EMPTY_CHANNEL,
        ),
    )


def role(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Role:
    """
    A role option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.

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
            utils.EMPTY_ROLE,
        ),
    )


def mentionable(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Snowflake:
    """
    A mentionable (snowflake) option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.

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
            hikari.Snowflake(0),
        ),
    )


def attachment(
    name: str,
    description: str,
    /,
    *,
    localize: bool = False,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Attachment:
    """
    An attachment option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        localize (:obj:`bool`): Whether to localize this option's name and description. If :obj:`true`, then the
            ``name`` and ``description`` arguments will instead be interpreted as localization keys from which the
            actual name and description will be retrieved. Defaults to :obj:`False`.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.

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
            utils.EMPTY_ATTACHMENT,
        ),
    )
