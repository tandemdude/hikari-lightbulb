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

__all__ = ["SlashCommand", "SlashCommandGroup", "SlashGroupMixin", "SlashSubGroup", "SlashSubCommand"]

import abc
import re
import typing as t

import hikari

from lightbulb import context as context_
from lightbulb import errors
from lightbulb.commands import base

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb import plugins

COMMAND_NAME_REGEX: re.Pattern[str] = re.compile(r"^[\w-]{1,32}$", re.U)


class SlashGroupMixin(abc.ABC):
    __slots__ = ()
    _plugin: t.Optional[plugins.Plugin]
    _subcommands: t.Dict[str, t.Union[SlashSubGroup, SlashSubCommand]]

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    def create_subcommands(
        self,
        raw_cmds: t.Sequence[base.CommandLike],
        app: app_.BotApp,
        allowed_types: t.Union[t.Tuple[t.Type[SlashSubCommand], t.Type[SlashSubGroup]], t.Type[SlashSubCommand]],
    ) -> None:
        for raw_cmd in raw_cmds:
            impls: t.List[t.Type[base.Command]] = getattr(raw_cmd.callback, "__cmd_types__", [])
            for impl in impls:
                if issubclass(impl, allowed_types):
                    cmd = impl(app, raw_cmd)
                    assert isinstance(cmd, (SlashSubCommand, SlashSubGroup))
                    cmd.parent = self  # type: ignore
                    cmd.plugin = self.plugin  # type: ignore

                    if cmd.name in self._subcommands:
                        raise errors.CommandAlreadyExists(
                            f"A prefix subcommand with name or alias {cmd.name!r} "
                            + f"already exists for group {self.name!r}"
                        )
                    self._subcommands[cmd.name] = cmd

    def recreate_subcommands(self, raw_cmds: t.Sequence[base.CommandLike], app: app_.BotApp) -> None:
        self._subcommands.clear()
        self.create_subcommands(
            raw_cmds, app, SlashSubCommand if isinstance(self, SlashSubGroup) else (SlashSubCommand, SlashSubGroup)
        )

    async def _invoke_subcommand(self, context: context_.base.Context) -> None:
        assert isinstance(context, context_.slash.SlashContext)
        cmd_option = context._raw_options[0]
        context._raw_options = cmd_option.options or []
        # Replace the invoked command prematurely so that _parse_options uses the correct command options
        context._invoked = self._subcommands[cmd_option.name]
        # Reparse the options for the subcommand
        context._parse_options(cmd_option.options)
        # Ensure we call _maybe_defer
        await context._maybe_defer()
        # Invoke the subcommand
        await context._invoked.invoke(context)

    def get_subcommand(self, name: str) -> t.Optional[t.Union[SlashSubGroup, SlashSubCommand]]:
        """Get the group's subcommand with the given name."""
        return self._subcommands.get(name)

    @property
    def subcommands(self) -> t.Dict[str, t.Union[SlashSubGroup, SlashSubCommand]]:
        """Mapping of command name to command object containing the group's subcommands."""
        return self._subcommands

    def _set_plugin(self, pl: plugins.Plugin) -> None:
        self._plugin = pl  # type: ignore[misc]
        for command in self._subcommands.values():
            if isinstance(command, SlashGroupMixin):
                command._set_plugin(pl)
            else:
                command.plugin = pl


class SlashCommand(base.ApplicationCommand):
    """
    An implementation of :obj:`~.commands.base.Command` representing a slash command.

    See the `API Documentation <https://discord.com/developers/docs/interactions/application-commands#slash-commands>`_.
    """

    __slots__ = ()

    def as_create_kwargs(self) -> t.Dict[str, t.Any]:
        sorted_opts = sorted(self.options.values(), key=lambda o: int(o.required), reverse=True)
        return {
            "type": hikari.CommandType.SLASH,
            "name": self.name,
            "description": self.description,
            "options": [o.as_application_command_option() for o in sorted_opts],
            "name_localizations": self.name_localizations,
            "description_localizations": self.description_localizations,
        }

    def _validate_attributes(self) -> None:
        if not COMMAND_NAME_REGEX.fullmatch(self.name) or self.name != self.name.lower():
            raise ValueError(
                f"Slash command {self.name!r}: name must match regex '^[\\w-]{1,32}$' and be all lowercase"
            ) from None
        if len(self.description) < 1 or len(self.description) > 100:
            raise ValueError(f"Slash command {self.name!r}: description must be from 1-100 characters long") from None
        if len(self.options) > 25:
            raise ValueError(f"Slash command {self.name!r}: can at most have 25 options") from None


class SlashSubCommand(SlashCommand, base.SubCommandTrait):
    """Class representing a slash subcommand."""

    __slots__ = ()

    @property
    def qualname(self) -> str:
        assert self.parent is not None
        return f"{self.parent.qualname} {self.name}"

    def as_option(self) -> hikari.CommandOption:
        sorted_opts = sorted(self.options.values(), key=lambda o: int(o.required), reverse=True)
        return hikari.CommandOption(
            type=hikari.OptionType.SUB_COMMAND,
            name=self.name,
            description=self.description,
            is_required=False,
            options=[o.as_application_command_option() for o in sorted_opts],
            name_localizations=self.name_localizations,
            description_localizations=self.description_localizations,
        )


class SlashSubGroup(SlashCommand, SlashGroupMixin, base.SubCommandTrait):
    """Class representing a slash subgroup of commands."""

    __slots__ = ("_raw_subcommands", "_subcommands")

    def __init__(self, app: app_.BotApp, initialiser: base.CommandLike) -> None:
        super().__init__(app, initialiser)
        self._raw_subcommands = initialiser.subcommands
        initialiser.subcommands = (
            initialiser.subcommands.add_parent(self)  # type: ignore
            if isinstance(initialiser.subcommands, base._SubcommandListProxy)  # type: ignore
            else base._SubcommandListProxy(initialiser.subcommands, parent=self)
        )
        # Just to keep mypy happy we leave SlashSubGroup here
        self._subcommands: t.Dict[str, t.Union[SlashSubGroup, SlashSubCommand]] = {}
        self.create_subcommands(self._raw_subcommands, app, SlashSubCommand)

    @property
    def qualname(self) -> str:
        assert self.parent is not None
        return f"{self.parent.qualname} {self.name}"

    def as_option(self) -> hikari.CommandOption:
        return hikari.CommandOption(
            type=hikari.OptionType.SUB_COMMAND_GROUP,
            name=self.name,
            description=self.description,
            is_required=False,
            options=[c.as_option() for c in self._subcommands.values()],
            name_localizations=self.name_localizations,
            description_localizations=self.description_localizations,
        )

    async def invoke(self, context: context_.base.Context, **_: t.Any) -> None:
        await self._invoke_subcommand(context)

    def _validate_attributes(self) -> None:
        super()._validate_attributes()
        if len(self._subcommands) > 25:
            raise ValueError(f"Slash command {self.name!r}: group can have at most 25 subcommands") from None

    def _set_plugin(self, pl: plugins.Plugin) -> None:
        SlashGroupMixin._set_plugin(self, pl)


class SlashCommandGroup(SlashCommand, SlashGroupMixin):
    """Class representing a slash command group."""

    __slots__ = ("_raw_subcommands", "_subcommands")

    def __init__(self, app: app_.BotApp, initialiser: base.CommandLike) -> None:
        super().__init__(app, initialiser)
        self._raw_subcommands = initialiser.subcommands
        initialiser.subcommands = (
            initialiser.subcommands.add_parent(self)  # type: ignore
            if isinstance(initialiser.subcommands, base._SubcommandListProxy)  # type: ignore
            else base._SubcommandListProxy(initialiser.subcommands, parent=self)
        )
        self._subcommands: t.Dict[str, t.Union[SlashSubGroup, SlashSubCommand]] = {}
        self.create_subcommands(self._raw_subcommands, app, (SlashSubCommand, SlashSubGroup))

    async def invoke(self, context: context_.base.Context, **_: t.Any) -> None:
        await self._invoke_subcommand(context)

    def as_create_kwargs(self) -> t.Dict[str, t.Any]:
        return {
            "type": hikari.CommandType.SLASH,
            "name": self.name,
            "description": self.description,
            "options": [c.as_option() for c in self._subcommands.values()],
            "name_localizations": self.name_localizations,
            "description_localizations": self.description_localizations,
        }

    def _validate_attributes(self) -> None:
        super()._validate_attributes()
        if len(self._subcommands) > 25:
            raise ValueError(f"Slash command {self.name!r}: group can have at most 25 subcommands") from None

    def _set_plugin(self, pl: plugins.Plugin) -> None:
        SlashGroupMixin._set_plugin(self, pl)
