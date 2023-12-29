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
_PRIMITIVE_OPTION_TYPES = (
    hikari.OptionType.STRING,
    hikari.OptionType.INTEGER,
    hikari.OptionType.FLOAT,
    hikari.OptionType.BOOLEAN,
    hikari.OptionType.MENTIONABLE,
)


@attr.define(frozen=True, kw_only=True, slots=True)
class CommandData:
    type: hikari.CommandType
    name: str
    description: str
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
        if option._data.name in context.command._resolved_option_cache:
            return t.cast(T, context.command._resolved_option_cache[option._data.name])

        # TODO - groups
        options = context.interaction.options
        if options is None:
            raise ValueError("options is None ??")

        found = [opt for opt in options if opt.name == option._data.name]

        if not found or (option._data.type not in _PRIMITIVE_OPTION_TYPES and context.interaction.resolved is None):
            if option._data.default is hikari.UNDEFINED:
                # error lol
                raise ValueError("no option resolved and no default provided")

            return option._data.default

        if option._data.type in _PRIMITIVE_OPTION_TYPES:
            context.command._resolved_option_cache[option._data.name] = found[0].value
            return t.cast(T, found[0].value)

        snowflake = found[0].value
        resolved = context.interaction.resolved
        option_type = option._data.type

        assert isinstance(snowflake, hikari.Snowflake)
        assert resolved is not None

        resolved_option: t.Any
        if option_type is hikari.OptionType.USER:
            resolved_option = resolved.members.get(snowflake) or resolved.users[snowflake]
        elif option_type is hikari.OptionType.ROLE:
            resolved_option = resolved.roles[snowflake]
        elif option_type is hikari.OptionType.CHANNEL:
            resolved_option = resolved.channels[snowflake]
        elif option_type is hikari.OptionType.ATTACHMENT:
            resolved_option = resolved.attachments[snowflake]
        else:
            raise TypeError("unsupported option type passed")

        context.command._resolved_option_cache[option._data.name] = resolved_option
        return t.cast(T, resolved_option)


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
