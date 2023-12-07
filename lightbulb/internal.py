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

__all__ = ["serialise_command", "manage_application_commands"]

import logging
import typing as t

import hikari

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb.commands import base

_LOGGER = logging.getLogger("lightbulb.internal")


class _GuildIDCollection:
    __slots__ = ("ids",)

    def __init__(self, ids: t.Optional[t.Union[t.Sequence[int], int]]):
        if ids is None:
            ids = []
        elif isinstance(ids, int):
            ids = [ids]
        self.ids: t.List[int] = list(ids)

    def __eq__(self, other: t.Any) -> bool:
        if not isinstance(other, int):
            return NotImplemented
        return other in self.ids

    def __repr__(self) -> str:
        return f"Guilds({', '.join(str(i) for i in self.ids)})"


def _serialise_option(option: hikari.CommandOption) -> t.Dict[str, t.Any]:
    return {
        "type": option.type,
        "name": option.name,
        "description": option.description,
        "is_required": option.is_required,
        "choices": list(
            sorted(
                [{"n": c.name, "v": c.value} for c in option.choices] if option.choices is not None else [],
                key=lambda d: d["n"],
            )
        ),
        "options": [_serialise_option(o) for o in option.options] if option.options is not None else [],
        "channel_types": list(sorted(option.channel_types if option.channel_types is not None else [])),
        "min_value": option.min_value,
        "max_value": option.max_value,
        "min_length": option.min_length,
        "max_length": option.max_length,
        "autocomplete": option.autocomplete,
    }


def _serialise_hikari_command(command: hikari.PartialCommand) -> t.Dict[str, t.Any]:
    options = sorted(getattr(command, "options", []) or [], key=lambda o: o.name)
    return {
        "type": command.type,
        "name": command.name,
        "description": getattr(command, "description", None) or None,
        "options": [_serialise_option(o) for o in options],
        "guild_id": command.guild_id or None,
        "default_member_permissions": command.default_member_permissions or None,
        "dm_enabled": command.is_dm_enabled,
        "nsfw": command.is_nsfw,
    }


def _serialise_lightbulb_command(command: base.ApplicationCommand) -> t.Dict[str, t.Any]:
    create_kwargs = command.as_create_kwargs()
    return {
        "type": create_kwargs["type"],
        "name": create_kwargs["name"],
        "description": create_kwargs.get("description"),
        "options": [_serialise_option(o) for o in sorted(create_kwargs.get("options", []), key=lambda o: o.name)],
        "guild_id": _GuildIDCollection(command.guilds) if command.guilds else None,
        "default_member_permissions": command.app_command_default_member_permissions,
        "dm_enabled": command.app_command_dm_enabled if not command.guilds else False,
        "nsfw": command.nsfw,
    }


def serialise_command(command: t.Union[hikari.PartialCommand, base.ApplicationCommand]) -> t.Dict[str, t.Any]:
    if isinstance(command, hikari.PartialCommand):
        return _serialise_hikari_command(command)
    return _serialise_lightbulb_command(command)


def _compare_commands(cmd1: base.ApplicationCommand, cmd2: hikari.PartialCommand) -> bool:
    return serialise_command(cmd1) == serialise_command(cmd2)


def _create_builder_from_command(
    app: app_.BotApp, cmd: t.Union[hikari.PartialCommand, base.ApplicationCommand]
) -> t.Union[hikari.api.SlashCommandBuilder, hikari.api.ContextMenuCommandBuilder]:
    bld: t.Union[hikari.api.SlashCommandBuilder, hikari.api.ContextMenuCommandBuilder]
    if isinstance(cmd, hikari.PartialCommand):
        if desc := getattr(cmd, "description", None):
            bld = app.rest.slash_command_builder(cmd.name, description=desc)
            for option in getattr(cmd, "options", []) or []:
                bld.add_option(option)
        else:
            bld = app.rest.context_menu_command_builder(cmd.type, cmd.name)

        bld.set_default_member_permissions(cmd.default_member_permissions)
        bld.set_is_dm_enabled(cmd.is_dm_enabled)
        bld.set_is_nsfw(cmd.is_nsfw)
        bld.set_name_localizations(cmd.name_localizations)
        bld.set_id(cmd.id)
    else:
        create_kwargs = cmd.as_create_kwargs()
        if "description" in create_kwargs:
            bld = app.rest.slash_command_builder(create_kwargs["name"], description=create_kwargs["description"])
            bld.set_description_localizations(cmd.description_localizations)
            for opt in create_kwargs.get("options", []):
                bld.add_option(opt)
        else:
            bld = app.rest.context_menu_command_builder(create_kwargs["type"], create_kwargs["name"])

        if cmd.app_command_default_member_permissions is not None:
            bld.set_default_member_permissions(cmd.app_command_default_member_permissions)
        bld.set_name_localizations(cmd.name_localizations)
        if isinstance(bld, hikari.api.SlashCommandBuilder):
            bld.set_description_localizations(cmd.description_localizations)
        bld.set_is_dm_enabled(cmd.app_command_dm_enabled)
        bld.set_is_nsfw(cmd.nsfw)

    return bld


def _get_lightbulb_command_equivalent(
    app: app_.BotApp, cmd: hikari.PartialCommand
) -> t.Optional[base.ApplicationCommand]:
    if cmd.type is hikari.CommandType.SLASH:
        return app.get_slash_command(cmd.name)
    elif cmd.type is hikari.CommandType.USER:
        return app.get_user_command(cmd.name)
    elif cmd.type is hikari.CommandType.MESSAGE:
        return app.get_message_command(cmd.name)


async def _get_guild_commands_to_set(app: app_.BotApp, guild_id: int) -> t.Sequence[hikari.api.CommandBuilder]:
    assert app.application is not None

    commands_to_declare = []
    unchanged, changed, created, deleted, skipped = 0, 0, 0, 0, 0
    # Get the commands that already exist in the given guild
    existing_commands = await app.rest.fetch_application_commands(app.application, guild_id)

    # Create a mapping containing all the commands that should be created for this guild
    app_commands: t.Dict[hikari.CommandType, t.Dict[str, base.ApplicationCommand]] = {
        hikari.CommandType.SLASH: {c.name: c for c in app._slash_commands.values() if guild_id in c.guilds},
        hikari.CommandType.USER: {c.name: c for c in app._user_commands.values() if guild_id in c.guilds},
        hikari.CommandType.MESSAGE: {c.name: c for c in app._message_commands.values() if guild_id in c.guilds},
    }
    for command in existing_commands:
        # Get the implementation for the given command
        equiv = _get_lightbulb_command_equivalent(app, command)
        if equiv is not None and guild_id not in equiv.guilds:
            equiv = None

        if equiv is None and not app._delete_unbound_commands:
            # Convert the hikari Command back into a builder because we don't want to delete it
            commands_to_declare.append(_create_builder_from_command(app, command))
            skipped += 1
        elif equiv is None and app._delete_unbound_commands:
            deleted += 1
        elif equiv is not None:
            if _compare_commands(equiv, command):
                # The commands are the same, create a builder from the hikari Command
                commands_to_declare.append(_create_builder_from_command(app, command))
                unchanged += 1
            else:
                # The commands are different, create a builder from the lightbulb Command
                commands_to_declare.append(_create_builder_from_command(app, equiv))
                changed += 1
        # Remove the command from the mapping, so we don't add a duplicate to the list
        app_commands[command.type].pop(command.name, None)

    # Add the remaining commands that do not have an equivalent on discord
    for cmds in app_commands.values():
        for cmd in cmds.values():
            commands_to_declare.append(_create_builder_from_command(app, cmd))
            created += 1

    _LOGGER.info("Processing application commands for guild %s", guild_id)
    _LOGGER.debug(
        "%s - Created: %s, Deleted: %s, Updated: %s, Unchanged: %s, Skipped: %s",
        guild_id,
        created,
        deleted,
        changed,
        unchanged,
        skipped,
    )

    return commands_to_declare


async def _process_global_commands(app: app_.BotApp) -> None:
    assert app.application is not None

    unchanged, changed, created, deleted, skipped = 0, 0, 0, 0, 0
    # Get the commands that already exist globally
    existing_global_commands = await app.rest.fetch_application_commands(app.application)
    # Create a mapping containing all the commands that should be created globally
    registered_global_commands: t.Dict[hikari.CommandType, t.Dict[str, base.ApplicationCommand]] = {
        hikari.CommandType.SLASH: {c.name: c for c in app._slash_commands.values() if not c.guilds},
        hikari.CommandType.USER: {c.name: c for c in app._user_commands.values() if not c.guilds},
        hikari.CommandType.MESSAGE: {c.name: c for c in app._message_commands.values() if not c.guilds},
    }
    for command in existing_global_commands:
        # Get the implementation for the given command
        equiv = registered_global_commands[command.type].get(command.name)
        if equiv is None:
            # No implementation for the hikari Command exists as a global command
            if app._delete_unbound_commands:
                # Delete the command
                await command.delete()
                deleted += 1
            else:
                # Ignore the command
                skipped += 1
        else:
            if _compare_commands(equiv, command):
                # The commands are the same, no need to recreate
                unchanged += 1
                equiv.instances[None] = command
            else:
                # The commands are different, recreate in order to update the version on discord
                await equiv.create()
                changed += 1
        # Remove the command from the mapping, so we don't make too many create calls
        registered_global_commands[command.type].pop(command.name, None)

    # Create the remaining commands that do not have an equivalent on discord
    for cmd_map in registered_global_commands.values():
        for app_cmd in cmd_map.values():
            await app_cmd.create()
            created += 1

    _LOGGER.debug(
        "Global - Created: %s, Deleted: %s, Updated: %s, Unchanged: %s, Skipped: %s",
        created,
        deleted,
        changed,
        unchanged,
        skipped,
    )


async def manage_application_commands(app: app_.BotApp) -> None:
    assert app.application is not None

    # Guild command processing
    _LOGGER.info("Processing guild application commands")
    all_guilds = set(app.default_enabled_guilds)
    for app_cmd in [*app._message_commands.values(), *app._user_commands.values(), *app._slash_commands.values()]:
        all_guilds.update(app_cmd.guilds or [])

    cmd_mapping: t.Dict[hikari.CommandType, t.Dict[str, base.ApplicationCommand]] = {
        hikari.CommandType.SLASH: app._slash_commands,  # type: ignore[dict-item]
        hikari.CommandType.USER: app._user_commands,  # type: ignore[dict-item]
        hikari.CommandType.MESSAGE: app._message_commands,  # type: ignore[dict-item]
    }
    for guild_id in all_guilds:
        cmds_to_declare = await _get_guild_commands_to_set(app, guild_id)
        created = await app.rest.set_application_commands(app.application, cmds_to_declare, guild_id)
        for created_cmd in created:
            if equiv := cmd_mapping[created_cmd.type].get(created_cmd.name):
                equiv.instances[guild_id] = created_cmd

    # Global command processing
    _LOGGER.info("Processing global application commands")
    await _process_global_commands(app)

    _LOGGER.info("Application command processing completed")
