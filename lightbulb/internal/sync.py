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

__all__ = []

import collections
import dataclasses
import logging
import typing as t

import hikari

from lightbulb.internal import constants
from lightbulb.internal.utils import non_undefined_or

if t.TYPE_CHECKING:
    from lightbulb import client as client_

LOGGER = logging.getLogger("lightbulb.internal.sync")


@dataclasses.dataclass(slots=True)
class CommandBuilderCollection:
    slash: t.Optional[hikari.api.SlashCommandBuilder] = None
    user: t.Optional[hikari.api.ContextMenuCommandBuilder] = None
    message: t.Optional[hikari.api.ContextMenuCommandBuilder] = None

    def put(self, bld: hikari.api.CommandBuilder) -> None:
        if isinstance(bld, hikari.api.SlashCommandBuilder):
            self.slash = bld
        elif isinstance(bld, hikari.api.ContextMenuCommandBuilder):
            if bld.type is hikari.CommandType.USER:
                self.user = bld
            else:
                self.message = bld
        else:
            raise TypeError("unrecognised builder type")


def hikari_command_to_builder(
    cmd: hikari.PartialCommand,
) -> t.Union[hikari.api.SlashCommandBuilder, hikari.api.ContextMenuCommandBuilder]:
    bld: t.Union[hikari.api.SlashCommandBuilder, hikari.api.ContextMenuCommandBuilder]
    if desc := getattr(cmd, "description", None):
        bld = hikari.impl.SlashCommandBuilder(cmd.name, description=desc)
        for option in getattr(cmd, "options", []) or []:
            bld.add_option(option)
    else:
        bld = hikari.impl.ContextMenuCommandBuilder(type=cmd.type, name=cmd.name)

    return (
        bld.set_default_member_permissions(cmd.default_member_permissions)
        .set_is_dm_enabled(cmd.is_dm_enabled)
        .set_is_nsfw(cmd.is_nsfw)
        .set_name_localizations(cmd.name_localizations)
        .set_id(cmd.id)
    )


async def get_existing_and_registered_commands(
    client: client_.Client, application: hikari.PartialApplication, guild: hikari.UndefinedOr[hikari.Snowflakeish]
) -> t.Tuple[t.Dict[str, CommandBuilderCollection], t.Dict[str, CommandBuilderCollection]]:
    existing: t.Dict[str, CommandBuilderCollection] = collections.defaultdict(CommandBuilderCollection)
    registered: t.Dict[str, CommandBuilderCollection] = collections.defaultdict(CommandBuilderCollection)

    for existing_command in await client.rest.fetch_application_commands(application, guild=guild):
        existing[existing_command.name].put(hikari_command_to_builder(existing_command))
    for name, collection in client._commands.get(
        constants.GLOBAL_COMMAND_KEY if guild is hikari.UNDEFINED else guild, {}
    ).items():
        for item in [collection.slash, collection.user, collection.message]:
            if item is None:
                continue

            registered[name].put(item.as_command_builder(client.default_locale, client.localization_provider))

    return existing, registered


def serialize_builder(bld: hikari.api.CommandBuilder) -> t.Dict[str, t.Any]:
    def serialize_option(opt: hikari.CommandOption) -> t.Dict[str, t.Any]:
        return {
            "type": opt.type,
            "name": opt.name,
            "description": opt.description,
            "is_required": opt.is_required,
            "choices": opt.choices or [],
            "options": [serialize_option(o) for o in (opt.options or [])],
            "channel_types": opt.channel_types or [],
            "autocomplete": opt.autocomplete,
            "min_value": opt.min_value,
            "max_value": opt.max_value,
            "name_localizations": opt.name_localizations,
            "description_localizations": opt.description_localizations,
            "min_length": opt.min_length,
            "max_length": opt.max_length,
        }

    out: t.Dict[str, t.Any] = {
        "name": bld.name,
        "is_dm_enabled": non_undefined_or(bld.is_dm_enabled, True),
        "is_nsfw": non_undefined_or(bld.is_nsfw, False),
        "name_localizations": bld.name_localizations,
    }

    if isinstance(bld, hikari.api.SlashCommandBuilder):
        out["description"] = bld.description
        out["description_localizations"] = bld.description_localizations
        out["options"] = [serialize_option(opt) for opt in bld.options]

    return out


def get_commands_to_set(
    existing: t.Dict[str, CommandBuilderCollection],
    registered: t.Dict[str, CommandBuilderCollection],
    delete_unknown: bool,
) -> t.Optional[t.Sequence[hikari.api.CommandBuilder]]:
    created, deleted, updated, unchanged = 0, 0, 0, 0

    commands_to_set: t.List[hikari.api.CommandBuilder] = []
    for name in {*existing.keys(), *registered.keys()}:
        existing_cmds, registered_cmds = existing[name], registered[name]
        for existing_bld, registered_bld in zip(
            [existing_cmds.slash, existing_cmds.user, existing_cmds.message],
            [registered_cmds.slash, registered_cmds.user, registered_cmds.message],
        ):
            if existing_bld is None and registered_bld is None:
                continue

            if existing_bld is None:
                assert registered_bld is not None

                commands_to_set.append(registered_bld)
                created += 1
            elif registered_bld is None:
                if delete_unknown:
                    deleted += 1
                else:
                    commands_to_set.append(existing_bld)
            else:
                if serialize_builder(existing_bld) != serialize_builder(registered_bld):
                    commands_to_set.append(registered_bld)
                    updated += 1
                else:
                    commands_to_set.append(existing_bld)
                    unchanged += 1

    LOGGER.debug("created: %s, deleted: %s, updated: %s, unchanged: %s", created, deleted, updated, unchanged)
    return commands_to_set if any([created, deleted, updated]) else None


async def sync_application_commands(client: client_.Client) -> None:
    application = await client._ensure_application()

    LOGGER.info("syncing global commands")
    existing_global_commands, registered_global_commands = await get_existing_and_registered_commands(
        client, application, hikari.UNDEFINED
    )
    global_commands_to_set = get_commands_to_set(
        existing_global_commands, registered_global_commands, client.delete_unknown_commands
    )
    if global_commands_to_set is not None:
        await client.rest.set_application_commands(application, global_commands_to_set)
    LOGGER.info("finished syncing global commands")

    for guild in client._commands:
        if guild == constants.GLOBAL_COMMAND_KEY:
            continue

        LOGGER.info("syncing commands for guild '%s'", guild)
        existing_guild_commands, registered_guild_commands = await get_existing_and_registered_commands(
            client, application, guild
        )
        guild_commands_to_set = get_commands_to_set(
            existing_guild_commands, registered_guild_commands, client.delete_unknown_commands
        )
        if guild_commands_to_set is not None:
            await client.rest.set_application_commands(application, guild_commands_to_set, guild=guild)
        LOGGER.info("finished syncing commands for guild '%s'", guild)
