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

__all__ = ["SubGroup", "Group"]

import abc
import dataclasses
import typing as t

import hikari

from lightbulb.commands import utils

if t.TYPE_CHECKING:
    from lightbulb import localization
    from lightbulb.commands import commands

CommandT = t.TypeVar("CommandT", bound=t.Type["commands.CommandBase"])
SubGroupCommandMappingT = t.Dict[str, t.Type["commands.CommandBase"]]
GroupCommandMappingT = t.Dict[str, t.Union["SubGroup", t.Type["commands.CommandBase"]]]


class GroupMixin(abc.ABC):
    """Base class for application command groups."""

    __slots__ = ()

    _commands: t.Union[SubGroupCommandMappingT, GroupCommandMappingT]

    @t.overload
    def register(self) -> t.Callable[[CommandT], CommandT]: ...

    @t.overload
    def register(self, command: CommandT) -> CommandT: ...

    def register(self, command: t.Optional[CommandT] = None) -> t.Union[CommandT, t.Callable[[CommandT], CommandT]]:
        """
        Register a command as a subcommand for this group. Can be used as a first or second order decorator,
        or called with the command to register.

        Args:
            command (:obj:`~typing.Type` [ :obj:`~lightbulb.commands.commands.CommandBase` ]): The command to register
                to the group as a subcommand.

        Returns:
            The passed command, with the parent set.

        Example:

            .. code-block:: python

                group = lightbulb.Group("name", "description")

                # valid
                @group.register  # or @group.register()
                class Example(
                    lightbulb.SlashCommand,
                    ...
                ):
                    ...

                # also valid
                group.register(Example)
        """
        if command is not None:
            self._commands[command._command_data.name] = command
            command._command_data.parent = self  # type: ignore[reportGeneralTypeIssues]
            return command

        def _inner(_command: CommandT) -> CommandT:
            return self.register(_command)

        return _inner

    def resolve_subcommand(self, path: t.List[str]) -> t.Optional[t.Type[commands.CommandBase]]:
        """
        Resolve the subcommand for the given path - fully qualified command name.

        Args:
            path (:obj:`~typing.List` [ :obj:`str` ]): The path of the subcommand to resolve.

        Returns:
            The resolved command class, or :obj:`None` if one was not found.
        """
        if not path:
            return None

        maybe_command = self._commands.get(path.pop(0))
        if maybe_command is None:
            return None

        if isinstance(maybe_command, GroupMixin):
            return maybe_command.resolve_subcommand(path)

        return maybe_command


@dataclasses.dataclass(slots=True, frozen=True)
class SubGroup(GroupMixin):
    """
    Dataclass representing a slash command subgroup.

    Warning:
        This **should not** be instantiated manually - you should instead create one using :meth:`Group.subgroup`.
    """

    name: str
    """The name of the subgroup."""
    description: str
    """The description of the subgroup."""
    localize: bool
    """Whether the group name and description should be localized."""
    parent: Group
    """The parent group of the subgroup."""
    _commands: SubGroupCommandMappingT = dataclasses.field(init=False, default_factory=dict)

    def to_command_option(
        self, default_locale: hikari.Locale, localization_provider: localization.LocalizationProviderT
    ) -> hikari.CommandOption:
        """
        Convert the subgroup into a subgroup command option.

        Returns:
            :obj:`hikari.CommandOption`: The subgroup option for this subgroup.
        """
        name, description = self.name, self.description
        name_localizations: t.Mapping[hikari.Locale, str] = {}
        description_localizations: t.Mapping[hikari.Locale, str] = {}

        if self.localize:
            name, description, name_localizations, description_localizations = utils.localize_name_and_description(
                name, description, default_locale, localization_provider
            )

        return hikari.CommandOption(
            type=hikari.OptionType.SUB_COMMAND_GROUP,
            name=name,
            name_localizations=name_localizations,  # type: ignore[reportArgumentType]
            description=description,
            description_localizations=description_localizations,  # type: ignore[reportArgumentType]
            options=[
                command.to_command_option(default_locale, localization_provider) for command in self._commands.values()
            ],
        )


@dataclasses.dataclass(slots=True, frozen=True)
class Group(GroupMixin):
    """
    Dataclass representing a slash command group.

    Note:
        If ``localize`` is :obj:`True`, then ``name`` and ``description`` will instead be
        interpreted as localization keys from which the actual name and description will be retrieved from.
    """

    name: str
    """The name of the group."""
    description: str
    """The description of the group."""
    localize: bool = False
    """Whether the group name and description should be localized."""
    nsfw: bool = False
    """Whether the group should be marked as nsfw. Defaults to :obj:`False`."""
    dm_enabled: bool = True
    """Whether the group is enabled in direct messages."""
    default_member_permissions: hikari.UndefinedOr[hikari.Permissions] = hikari.UNDEFINED
    """The default permissions required to use the group in a guild."""

    _commands: GroupCommandMappingT = dataclasses.field(init=False, default_factory=dict)

    def subgroup(self, name: str, description: str, *, localize: bool = False) -> SubGroup:
        """
        Create a new subgroup as a child of this group.

        Args:
            name (:obj:`str`): The name of the subgroup.
            description (:obj:`str`): The description of the subgroup.
            localize (:obj:`bool`, optional): Whether to localize the group's name and description. If :obj:`true`,
                then the ``name`` and ``description`` arguments will instead be interpreted as localization keys from
                which the actual name and description will be retrieved from. Defaults to :obj:`False`.

        Returns:
            :obj:`~SubGroup`: The created subgroup.
        """
        new = SubGroup(name=name, description=description, localize=localize, parent=self)
        self._commands[name] = new
        return new

    def as_command_builder(
        self, default_locale: hikari.Locale, localization_provider: localization.LocalizationProviderT
    ) -> hikari.api.CommandBuilder:
        """
        Convert the group into a hikari command builder object.

        Returns:
            :obj:`hikari.api.CommandBuilder`: The builder object for this group.
        """
        name, description = self.name, self.description
        name_localizations: t.Mapping[hikari.Locale, str] = {}
        description_localizations: t.Mapping[hikari.Locale, str] = {}

        if self.localize:
            name, description, name_localizations, description_localizations = utils.localize_name_and_description(
                name, description, default_locale, localization_provider
            )

        bld = (
            hikari.impl.SlashCommandBuilder(name=name, description=description)
            .set_name_localizations(name_localizations)  # type: ignore[reportArgumentType]
            .set_description_localizations(description_localizations)  # type: ignore[reportArgumentType]
            .set_is_nsfw(self.nsfw)
            .set_is_dm_enabled(self.dm_enabled)
            .set_default_member_permissions(self.default_member_permissions)
        )

        for command_or_group in self._commands.values():
            bld.add_option(command_or_group.to_command_option(default_locale, localization_provider))

        return bld
