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

__all__ = ["PrefixCommand", "PrefixSubCommand", "PrefixSubGroup", "PrefixCommandGroup", "PrefixGroupMixin"]

import abc
import typing as t

from multidict import CIMultiDict

from lightbulb import context as context_
from lightbulb import errors
from lightbulb.commands import base

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb import plugins


class PrefixGroupMixin(abc.ABC):
    __slots__ = ()
    name: str
    _plugin: t.Optional[plugins.Plugin]
    _subcommands: t.Dict[str, t.Union[PrefixSubGroup, PrefixSubCommand]]

    def maybe_resolve_subcommand(
        self, arg_string: str
    ) -> t.Tuple[t.Optional[t.Union[PrefixSubGroup, PrefixSubCommand]], str]:
        if not arg_string:
            return None, ""

        maybe_subcmd, *remainder = arg_string.split(maxsplit=1)
        remainder = "".join(remainder)

        if (cmd := self._subcommands.get(maybe_subcmd)) is not None:
            return cmd, remainder
        return None, ""

    def create_subcommands(self, raw_cmds: t.Sequence[base.CommandLike], app: app_.BotApp) -> None:
        for raw_cmd in raw_cmds:
            impls: t.List[t.Type[base.Command]] = getattr(raw_cmd.callback, "__cmd_types__", [])
            for impl in impls:
                if issubclass(impl, (PrefixSubCommand, PrefixSubGroup)):
                    cmd = impl(app, raw_cmd)
                    cmd.parent = self  # type: ignore
                    cmd.plugin = self.plugin  # type: ignore

                    for name in [cmd.name, *cmd.aliases]:
                        if name in self._subcommands:
                            raise errors.CommandAlreadyExists(
                                f"A prefix subcommand with name or alias {name!r} already exists for group {self.name!r}"
                            )
                        self._subcommands[name] = cmd

    def recreate_subcommands(self, raw_cmds: t.Sequence[base.CommandLike], app: app_.BotApp) -> None:
        self._subcommands.clear()
        self.create_subcommands(raw_cmds, app)

    def get_subcommand(self, name: str) -> t.Optional[t.Union[PrefixSubGroup, PrefixSubCommand]]:
        return self._subcommands.get(name)

    @property
    def subcommands(self) -> t.Dict[str, t.Union[PrefixSubGroup, PrefixSubCommand]]:
        """Mapping of command name to command object containing the group's subcommands."""
        return self._subcommands

    def _set_plugin(self, pl: plugins.Plugin) -> None:
        self._plugin = pl
        for command in self._subcommands.values():
            if isinstance(command, PrefixGroupMixin):
                command._set_plugin(pl)
            else:
                command.plugin = pl


class PrefixCommand(base.Command):
    """
    An implementation of :obj:`~.commands.base.Command` representing a prefix command.
    """

    __slots__ = ()

    @property
    def signature(self) -> str:
        sig = self.qualname
        if self.options:
            sig += f" {' '.join(f'<{o.name}>' if o.required else f'[{o.name}={o.default}]' for o in self.options.values())}"
        return sig

    async def invoke(self, context: context_.base.Context) -> None:
        context._invoked = self
        await self.evaluate_checks(context)
        await self.evaluate_cooldowns(context)
        assert isinstance(context, context_.prefix.PrefixContext)
        await context._parser.inject_args_to_context()
        await self(context)

    def _validate_attributes(self) -> None:
        if " " in self.name:
            raise ValueError(f"Prefix command {self.name!r}: name cannot contain spaces") from None


class PrefixSubCommand(PrefixCommand, base.SubCommandTrait):
    """
    Class representing a prefix subcommand.
    """

    __slots__ = ()

    @property
    def qualname(self) -> str:
        assert self.parent is not None
        return f"{self.parent.qualname} {self.name}"

    async def invoke(self, context: context_.base.Context, *, arg_buffer: str = "") -> None:
        context._invoked = self
        assert isinstance(context, context_.prefix.PrefixContext)
        context._parser = type(context._parser)(context, arg_buffer)
        context._parser.options = list(self.options.values())
        await super().invoke(context)


class PrefixSubGroup(PrefixCommand, PrefixGroupMixin, base.SubCommandTrait):
    """
    Class representing a prefix subgroup of commands.
    """

    __slots__ = ("_raw_subcommands", "_subcommands")

    def __init__(self, app: app_.BotApp, initialiser: base.CommandLike) -> None:
        super().__init__(app, initialiser)
        self._raw_subcommands = initialiser.subcommands
        initialiser.subcommands = base._SubcommandListProxy(initialiser.subcommands, parent=self)  # type: ignore
        self._subcommands = {} if not app._case_insensitive_prefix_commands else CIMultiDict()  # type: ignore
        self.create_subcommands(self._raw_subcommands, app)

    @property
    def qualname(self) -> str:
        assert self.parent is not None
        return f"{self.parent.qualname} {self.name}"

    async def invoke(self, context: context_.base.Context, *, arg_buffer: str = "") -> None:
        context._invoked = self
        subcmd, remainder = self.maybe_resolve_subcommand(arg_buffer)
        if subcmd is not None:
            await subcmd.invoke(context, arg_buffer=remainder)
            return

        assert isinstance(context, context_.prefix.PrefixContext)
        context._parser = type(context._parser)(context, arg_buffer)
        context._parser.options = list(self.options.values())
        await super().invoke(context)

    def _validate_attributes(self) -> None:
        super()._validate_attributes()
        for command in self._subcommands.values():
            command._validate_attributes()

    def _set_plugin(self, pl: plugins.Plugin) -> None:
        PrefixGroupMixin._set_plugin(self, pl)


class PrefixCommandGroup(PrefixCommand, PrefixGroupMixin):
    """
    Class representing a prefix command group.
    """

    __slots__ = ("_raw_subcommands", "_subcommands")

    def __init__(self, app: app_.BotApp, initialiser: base.CommandLike) -> None:
        super().__init__(app, initialiser)
        self._raw_subcommands = initialiser.subcommands
        initialiser.subcommands = base._SubcommandListProxy(initialiser.subcommands, parent=self)  # type: ignore
        self._subcommands = {} if not app._case_insensitive_prefix_commands else CIMultiDict()  # type: ignore
        self.create_subcommands(self._raw_subcommands, app)

    async def invoke(self, context: context_.base.Context) -> None:
        context._invoked = self
        assert isinstance(context, context_.prefix.PrefixContext) and context.event.message.content is not None

        subcmd, remainder = self.maybe_resolve_subcommand(
            context.event.message.content[len(context.prefix) + len(context.invoked_with) :].strip()
        )
        if subcmd is not None:
            await subcmd.invoke(context, arg_buffer=remainder)
            return

        await super().invoke(context)

    def _validate_attributes(self) -> None:
        super()._validate_attributes()
        for command in self._subcommands.values():
            command._validate_attributes()

    def _set_plugin(self, pl: plugins.Plugin) -> None:
        PrefixGroupMixin._set_plugin(self, pl)
