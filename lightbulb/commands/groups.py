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

__all__ = ["Group", "SubGroup"]

import abc
import dataclasses
import typing as t

import hikari

from lightbulb.commands import commands
from lightbulb.commands import utils

if t.TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence

    from lightbulb import localization

CommandT = t.TypeVar("CommandT", bound=type["commands.CommandBase"])
SubGroupCommandMappingT = dict[str, type["commands.CommandBase"]]
GroupCommandMappingT = dict[str, t.Union["SubGroup", type["commands.CommandBase"]]]


class GroupMixin(abc.ABC):
    """Base class for application command groups."""

    __slots__ = ()

    _commands: SubGroupCommandMappingT | GroupCommandMappingT

    @t.overload
    def register(self) -> Callable[[CommandT], CommandT]: ...

    @t.overload
    def register(self, command: CommandT) -> CommandT: ...

    def register(self, command: CommandT | None = None) -> CommandT | Callable[[CommandT], CommandT]:
        """
        Register a command as a subcommand for this group. Can be used as a first or second order decorator,
        or called with the command to register.

        Args:
            command: The command to register to the group as a subcommand.

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
    localize: bool = dataclasses.field(repr=False)
    """Whether the group name and description should be localized."""
    parent: Group = dataclasses.field(repr=False)
    """The parent group of the subgroup."""

    _commands: SubGroupCommandMappingT = dataclasses.field(init=False, hash=False, repr=False, default_factory=dict)  # type: ignore[reportUnknownVariableType]

    @property
    def _command_data(self) -> commands.CommandData:
        cdata = commands.CommandData(
            hikari.CommandType.SLASH,
            self.name,
            self.description,
            self.localize,
            self.parent.nsfw,
            self.parent.integration_types,
            self.parent.contexts,
            self.parent.default_member_permissions,
            [],
            {},
            "",
        )
        cdata.parent = self.parent
        return cdata

    @property
    def subcommands(self) -> SubGroupCommandMappingT:
        """The subcommands of this subgroup."""
        return self._commands

    async def to_command_option(
        self, default_locale: hikari.Locale, localization_provider: localization.LocalizationProvider
    ) -> hikari.CommandOption:
        """
        Convert the subgroup into a subgroup command option.

        Returns:
            :obj:`hikari.CommandOption`: The subgroup option for this subgroup.
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
            ) = await utils.localize_name_and_description(name, description, default_locale, localization_provider)

        return hikari.CommandOption(
            type=hikari.OptionType.SUB_COMMAND_GROUP,
            name=name,
            name_localizations=name_localizations,  # type: ignore[reportArgumentType]
            description=description,
            description_localizations=description_localizations,  # type: ignore[reportArgumentType]
            options=[
                await command.to_command_option(default_locale, localization_provider)
                for command in self._commands.values()
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
    localize: bool = dataclasses.field(repr=False, default=False)
    """Whether the group name and description should be localized."""
    nsfw: bool = dataclasses.field(repr=False, default=False)
    """Whether the group should be marked as nsfw. Defaults to :obj:`False`."""
    integration_types: hikari.UndefinedOr[Sequence[hikari.ApplicationIntegrationType]] = dataclasses.field(
        hash=False, repr=False, default=hikari.UNDEFINED
    )
    """Installation contexts where the command is available. Only affects global commands."""
    contexts: hikari.UndefinedOr[Sequence[hikari.ApplicationContextType]] = dataclasses.field(
        hash=False, repr=False, default=hikari.UNDEFINED
    )
    """Interaction contexts where the command can be used. Only affects global commands."""
    default_member_permissions: hikari.UndefinedOr[hikari.Permissions] = dataclasses.field(
        repr=False, default=hikari.UNDEFINED
    )
    """The default permissions required to use the group in a guild."""
    extension: str | None = dataclasses.field(init=False, repr=False, default=None)
    """The extensions that the command's loader was loaded from, or :obj:`None` if not applicable."""

    _commands: GroupCommandMappingT = dataclasses.field(init=False, hash=False, repr=False, default_factory=dict)  # type: ignore[reportUnknownVariableType]

    @property
    def _command_data(self) -> commands.CommandData:
        cdata = commands.CommandData(
            hikari.CommandType.SLASH,
            self.name,
            self.description,
            self.localize,
            self.nsfw,
            self.integration_types,
            self.contexts,
            self.default_member_permissions,
            [],
            {},
            "",
        )
        cdata.extension = self.extension
        return cdata

    @property
    def subcommands(self) -> GroupCommandMappingT:
        """The subcommands and subgroups of this group."""
        return self._commands

    def subgroup(self, name: str, description: str, *, localize: bool = False) -> SubGroup:
        """
        Create a new subgroup as a child of this group.

        Args:
            name: The name of the subgroup.
            description: The description of the subgroup.
            localize: Whether to localize the group's name and description. If :obj:`true`,
                then the ``name`` and ``description`` arguments will instead be interpreted as localization keys from
                which the actual name and description will be retrieved from. Defaults to :obj:`False`.

        Returns:
            :obj:`~SubGroup`: The created subgroup.
        """
        new = SubGroup(name=name, description=description, localize=localize, parent=self)
        self._commands[name] = new
        return new

    async def as_command_builder(
        self, default_locale: hikari.Locale, localization_provider: localization.LocalizationProvider
    ) -> hikari.api.CommandBuilder:
        """
        Convert the group into a hikari command builder object.

        Returns:
            :obj:`hikari.api.CommandBuilder`: The builder object for this group.
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
            ) = await utils.localize_name_and_description(name, description, default_locale, localization_provider)

        bld = (
            hikari.impl.SlashCommandBuilder(name=name, description=description)
            .set_name_localizations(name_localizations)  # type: ignore[reportArgumentType]
            .set_description_localizations(description_localizations)  # type: ignore[reportArgumentType]
            .set_is_nsfw(self.nsfw)
            .set_default_member_permissions(self.default_member_permissions)
            .set_integration_types(self.integration_types)
            .set_context_types(self.contexts)
        )

        for command_or_group in self._commands.values():
            option = await command_or_group.to_command_option(default_locale, localization_provider)
            bld.add_option(option)

        return bld
