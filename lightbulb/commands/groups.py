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

import abc
import dataclasses
import typing as t

import hikari

if t.TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from lightbulb.commands import commands

CommandT = t.TypeVar("CommandT", bound=t.Type["commands.CommandBase"])
SubGroupCommandMappingT = t.Dict[str, t.Type["commands.CommandBase"]]
GroupCommandMappingT = t.Dict[str, t.Union["SubGroup", t.Type["commands.CommandBase"]]]


class GroupMixin(abc.ABC):
    __slots__ = ()

    _commands: t.Union[SubGroupCommandMappingT, GroupCommandMappingT]

    @t.overload
    def register(self) -> t.Callable[[CommandT], CommandT]:
        ...

    @t.overload
    def register(self, command: CommandT) -> CommandT:
        ...

    def register(self, command: t.Optional[CommandT] = None) -> t.Union[CommandT, t.Callable[[CommandT], CommandT]]:
        if command is not None:
            self._commands[command._.command_data.name] = command
            command._.command_data.parent = self  # type: ignore[reportGeneralTypeIssues]
            return command

        def _inner(_command: CommandT) -> CommandT:
            return self.register(_command)

        return _inner


@dataclasses.dataclass(slots=True, kw_only=True, frozen=True)
class SubGroup(GroupMixin):
    name: str
    description: str
    parent: Group
    _commands: SubGroupCommandMappingT = dataclasses.field(init=False, default_factory=dict)

    def to_command_option(self) -> hikari.CommandOption:
        # TODO - localisations
        return hikari.CommandOption(
            type=hikari.OptionType.SUB_COMMAND_GROUP,
            name=self.name,
            description=self.description,
            options=[command._.command_data.to_command_option() for command in self._commands.values()],
        )


@dataclasses.dataclass(slots=True, kw_only=True, frozen=True)
class Group(GroupMixin):
    name: str
    description: str
    nsfw: bool
    _commands: GroupCommandMappingT = dataclasses.field(init=False, default_factory=dict)

    def subgroup(self, name: str, description: str) -> SubGroup:
        new = SubGroup(name=name, description=description, parent=self)
        self._commands[name] = new
        return new

    def as_command_builder(self) -> hikari.api.CommandBuilder:
        # TODO - localisations
        bld = hikari.impl.SlashCommandBuilder(name=self.name, description=self.description)
        bld.set_is_nsfw(self.nsfw)

        for command_or_group in self._commands.values():
            bld.add_option(
                command_or_group.to_command_option()
                if isinstance(command_or_group, SubGroup)
                else command_or_group._.command_data.to_command_option()
            )

        return bld
