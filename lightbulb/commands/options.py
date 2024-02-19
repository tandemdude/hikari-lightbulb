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

import dataclasses
import typing as t

import hikari

from lightbulb import utils

if t.TYPE_CHECKING:
    from lightbulb import commands

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
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED
    """The default value for the option."""
    choices: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED  # TODO
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
    autocomplete: hikari.UndefinedOr[t.Any] = hikari.UNDEFINED  # TODO
    """TODO"""
    localizations: t.Any = hikari.UNDEFINED  # TODO
    """TODO"""

    def to_command_option(self) -> hikari.CommandOption:
        return hikari.CommandOption(
            type=self.type,
            name=self.name,
            description=self.description,
            is_required=self.default is not hikari.UNDEFINED,
            choices=_non_undefined_or(self.choices, None),
            channel_types=_non_undefined_or(self.channel_types, None),
            min_value=_non_undefined_or(self.min_value, None),
            max_value=_non_undefined_or(self.max_value, None),
            min_length=_non_undefined_or(self.min_length, None),
            max_length=_non_undefined_or(self.max_length, None),
            autocomplete=self.autocomplete is not hikari.UNDEFINED,
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

    __slots__ = ("_data", "_unbound_default")

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
    def __get__(self, instance: t.Optional[commands.UserCommand], owner: t.Type[commands.UserCommand]) -> hikari.User:
        ...

    @t.overload
    def __get__(
        self, instance: t.Optional[commands.MessageCommand], owner: t.Type[commands.MessageCommand]
    ) -> hikari.Message:
        ...

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


def string(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: t.Any = hikari.UNDEFINED,  # TODO
    min_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_length: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: t.Any = hikari.UNDEFINED,  # TODO
) -> str:
    """
    A string option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.
        choices: TODO
        min_length (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The minimum length for the option.
        max_length (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The maximum length for the option.
        autocomplete: TODO

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
                default=default,
                choices=choices,
                min_length=min_length,
                max_length=max_length,
                autocomplete=autocomplete,
            ),
            "",
        ),
    )


def integer(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: t.Any = hikari.UNDEFINED,  # TODO
    min_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[int] = hikari.UNDEFINED,
    autocomplete: t.Any = hikari.UNDEFINED,  # TODO
) -> int:
    """
    An integer option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.
        choices: TODO
        min_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The minimum value for the option.
        max_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`int` ]): The maximum value for the option.
        autocomplete: TODO

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
                default=default,
                choices=choices,
                min_value=min_value,
                max_value=max_value,
                autocomplete=autocomplete,
            ),
            0,
        ),
    )


def boolean(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> bool:
    """
    A boolean option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
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
                default=default,
            ),
            False,
        ),
    )


def number(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    choices: t.Any = hikari.UNDEFINED,  # TODO
    min_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    max_value: hikari.UndefinedOr[float] = hikari.UNDEFINED,
    autocomplete: t.Any = hikari.UNDEFINED,  # TODO
) -> float:
    """
    A numeric (float) option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
        default (:obj:`~hikari.undefined.UndefinedOr` [ ``D`` ]): The default value for the option.
        choices: TODO
        min_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`float` ]): The minimum value for the option.
        max_value (:obj:`~hikari.undefined.UndefinedOr` [ :obj:`float` ]): The maximum value for the option.
        autocomplete: TODO

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
                default=default,
                choices=choices,
                min_value=min_value,
                max_value=max_value,
                autocomplete=autocomplete,
            ),
            0.0,
        ),
    )


def user(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.User:
    """
    A user option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
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
                default=default,
            ),
            utils.EMPTY_USER,
        ),
    )


def channel(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
    channel_types: hikari.UndefinedOr[t.Sequence[hikari.ChannelType]] = hikari.UNDEFINED,
) -> hikari.PartialChannel:
    """
    A channel option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
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
                default=default,
                channel_types=channel_types,
            ),
            default_when_not_bound=utils.EMPTY_CHANNEL,
        ),
    )


def role(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Role:
    """
    A role option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
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
                default=default,
            ),
            utils.EMPTY_ROLE,
        ),
    )


def mentionable(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Snowflake:
    """
    A mentionable (snowflake) option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
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
                default=default,
            ),
            hikari.Snowflake(0),
        ),
    )


def attachment(
    name: str,
    description: str,
    default: hikari.UndefinedOr[D] = hikari.UNDEFINED,
) -> hikari.Attachment:
    """
    An attachment option.

    Args:
        name (:obj:`str`): The name of the option.
        description (:obj:`str`): The description of the option.
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
                default=default,
            ),
            utils.EMPTY_ATTACHMENT,
        ),
    )
