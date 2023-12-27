# -*- coding: utf-8 -*-
# Copyright © tandemdude 2023-present
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

import logging
import typing as t

import attr
import hikari

from lightbulb.commands import hooks as hooks_
from lightbulb.commands import options as options_
from lightbulb.commands.hooks import _HOOK_TYPE_ATTR

if t.TYPE_CHECKING:
    from lightbulb import context as context_

__all__ = ["CommandData", "CommandMeta", "CommandBase", "CommandUtils", "UserCommand", "MessageCommand", "SlashCommand"]

T = t.TypeVar("T")
D = t.TypeVar("D")
CommandT = t.TypeVar("CommandT", bound="CommandBase")

LOGGER = logging.getLogger("lightbulb.commands")


@attr.define(frozen=True, kw_only=True, slots=True)
class CommandData:
    type: hikari.CommandType
    name: str
    description: str
    guilds: t.Sequence[int]
    nsfw: bool
    localizations: t.Any  # TODO
    parent: t.Any  # TODO

    options: t.Mapping[str, options_.OptionData[t.Any]]
    hooks: t.Mapping[hooks_.HookType, str]

    def as_command_builder(self) -> hikari.api.CommandBuilder:
        if self.type is hikari.CommandType.SLASH:
            bld = hikari.impl.SlashCommandBuilder(name=self.name, description=self.description)
            for option in self.options.values():
                bld.add_option(option.to_command_option())
            return bld

        return hikari.impl.ContextMenuCommandBuilder(type=self.type, name=self.name)


class CommandMeta(type):
    __command_types: t.ClassVar[t.Dict[type, hikari.CommandType]] = {}

    @staticmethod
    def _is_option(item: t.Any) -> bool:
        return isinstance(item, options_.Option)

    @staticmethod
    def _is_hook(item: t.Any) -> bool:
        return (ht := getattr(item, _HOOK_TYPE_ATTR, None)) is not None and isinstance(ht, hooks_.HookType)

    def __new__(cls, cls_name: str, bases: t.Tuple[type, ...], attrs: t.Dict[str, t.Any], **kwargs: t.Any) -> type:
        cmd_type: hikari.CommandType
        # Bodge because I cannot figure out how to avoid initialising all the kwargs in our
        # own convenience classes any other way
        if "type" in kwargs:
            cmd_type = kwargs.pop("type")
            new_cls = super().__new__(cls, cls_name, bases, attrs, **kwargs)
            # Store the command type for our convenience class so that we can retrieve it when the
            # developer creates their own commands later
            CommandMeta.__command_types[new_cls] = cmd_type
            return new_cls

        # Find the convenience class that the new command inherits from so that we
        # can retrieve the command type that it implements
        base_cls = [base for base in bases if type(base) is CommandMeta]
        if len(base_cls) != 1:
            raise TypeError("commands must directly inherit from a single command class")
        cmd_type = CommandMeta.__command_types[base_cls[0]]

        cmd_name: str = kwargs.pop("name")
        description: str = kwargs.pop("description", "")
        # Only slash commands have descriptions
        if not description and cmd_type is hikari.CommandType.SLASH:
            raise TypeError("'description' is required for slash commands")

        guilds: t.Sequence[int] = kwargs.pop("guilds", ())
        nsfw: bool = kwargs.pop("nsfw", False)
        localizations: t.Any = kwargs.pop("localizations", None)
        parent: t.Any = kwargs.pop("parent", None)

        options: t.Dict[str, options_.OptionData[t.Any]] = {}
        hooks: t.Dict[hooks_.HookType, str] = {}
        for name, item in attrs.items():
            if cls._is_option(item):
                options[name] = item._data
            elif cls._is_hook(item):
                hook_type = getattr(item, _HOOK_TYPE_ATTR)
                if hook_type in hooks:
                    LOGGER.warning("Duplicate hook found for type %s in command %r - ignoring", hook_type, cls_name)
                else:
                    hooks[hook_type] = name

        if hooks_.HookType.ON_INVOKE not in hooks:
            raise TypeError("'on_invoke' hook is required but could not be found")

        attrs["_"] = CommandUtils(
            command_data=CommandData(
                type=cmd_type,
                name=cmd_name,
                description=description,
                guilds=guilds,
                nsfw=nsfw,
                localizations=localizations,
                parent=parent,
                options=options,
                hooks=hooks,
            )
        )

        return super().__new__(cls, cls_name, bases, attrs, **kwargs)


@attr.define(kw_only=True, slots=True)
class CommandUtils:
    command_data: CommandData

    def resolve_option(self, context: context_.Context, option: options_.Option[T, D]) -> t.Union[T, D]:
        # TODO - groups
        options = context.interaction.options
        if options is None:
            raise ValueError("options is None ??")

        found = [opt for opt in options if opt.name == option._data.name]

        if found:
            return t.cast(T, found[0].value)

        if option._data.default is hikari.UNDEFINED:
            # error lol
            raise ValueError("no option resolved and no default provided")

        return option._data.default


class CommandBase:
    __slots__ = ("_current_context", "_resolved_option_cache")

    _: t.ClassVar[CommandUtils]  # TODO - rename this to something that makes sense
    _current_context: t.Optional[context_.Context]
    _resolved_option_cache: t.MutableMapping[str, t.Any]

    def __new__(cls, *args: t.Any, **kwargs: t.Any) -> CommandBase:
        new = super().__new__(cls, *args, **kwargs)
        new._current_context = None
        new._resolved_option_cache = {}
        return new


class SlashCommand(CommandBase, metaclass=CommandMeta, type=hikari.CommandType.SLASH):
    __slots__ = ()


class UserCommand(CommandBase, metaclass=CommandMeta, type=hikari.CommandType.USER):
    __slots__ = ()

    target: hikari.User = t.cast(hikari.User, options_.ContextMenuOption(hikari.User))


class MessageCommand(CommandBase, metaclass=CommandMeta, type=hikari.CommandType.MESSAGE):
    __slots__ = ()

    target: hikari.Message = t.cast(hikari.Message, options_.ContextMenuOption(hikari.Message))
