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

import abc
import functools
import logging
import typing as t

import hikari

from lightbulb import commands
from lightbulb import context as context_

__all__ = ["Client", "GatewayEnabledClient", "RestEnabledClient"]

CommandT = t.TypeVar("CommandT", bound=t.Type[commands.CommandBase])
CommandMapT = t.MutableMapping[str, t.Type[commands.CommandBase]]

LOGGER = logging.getLogger("lightbulb.client")


class GatewayClientAppT(hikari.EventManagerAware, hikari.RESTAware, t.Protocol):
    ...


class RestClientAppT(hikari.InteractionServerAware, hikari.RESTAware, t.Protocol):
    ...


class Client(abc.ABC):
    __slots__ = ("_commands", "_rest", "_default_enabled_guilds", "_application")

    def __init__(self, rest: hikari.api.RESTClient, default_enabled_guilds: t.Sequence[hikari.Snowflakeish]) -> None:
        self._rest: hikari.api.RESTClient = rest
        self._default_enabled_guilds = default_enabled_guilds
        self._commands: CommandMapT = {}
        self._application: t.Optional[hikari.PartialApplication] = None

    def register(self, command: CommandT) -> CommandT:
        name = command._.command_data.name
        self._commands[name] = command
        LOGGER.debug("command %s registered successfully", name)
        return command

    async def _ensure_application(self) -> hikari.PartialApplication:
        if self._application is not None:
            return self._application

        self._application = await self._rest.fetch_application()
        return self._application

    async def sync_application_commands(self) -> None:
        # TODO - implement syncing logic - for now just do create
        LOGGER.info("syncing commands with discord")
        builders: t.List[hikari.api.CommandBuilder] = []
        for command in self._commands.values():
            builders.append(command._.command_data.as_command_builder())

        application = await self._ensure_application()

        if not self._default_enabled_guilds:
            await self._rest.set_application_commands(application, builders)

        for guild in self._default_enabled_guilds:
            await self._rest.set_application_commands(application, builders, guild)

        LOGGER.info("finished syncing commands with discord")

    @staticmethod
    def _get_subcommand(
        options: t.Sequence[hikari.CommandInteractionOption],
    ) -> t.Optional[hikari.CommandInteractionOption]:
        subcommand = filter(
            lambda o: o.type in (hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP), options
        )
        return next(subcommand, None)

    def build_context(
        self,
        interaction: hikari.CommandInteraction,
        options: t.Sequence[hikari.CommandInteractionOption],
        command: commands.CommandBase,
    ) -> context_.Context:
        return context_.Context(
            client=self,
            interaction=interaction,
            options=options,
            command=command,
        )

    async def handle_application_command_interaction(self, interaction: hikari.CommandInteraction) -> None:
        command_path = [interaction.command_name]

        subcommand: t.Optional[hikari.CommandInteractionOption]
        options = interaction.options
        while (subcommand := self._get_subcommand(options or [])) is not None:
            command_path.append(subcommand.name)
            options = subcommand.options

        command: t.Optional[t.Type[commands.CommandBase]] = self._commands.get(command_path[0])
        if command is None:
            LOGGER.debug("ignoring interaction create received for unknown command - %s", " ".join(command_path))
            return

        command_data = command._.command_data

        command_instance = command()
        context = self.build_context(
            interaction, getattr(subcommand, "options", interaction.options) or [], command_instance
        )
        command_instance._current_context = context
        command_instance._resolved_option_cache = {}

        if hook_name := command_data.hooks.get(commands.HookType.PRE_INVOKE):
            LOGGER.debug("%s - invoking pre-invoke hook", command_data.name)
            await getattr(command, hook_name)(command_instance, context)
        LOGGER.debug("%s - invoking command", command_data.name)
        await getattr(command, command_data.hooks[commands.HookType.ON_INVOKE])(command_instance, context)
        if hook_name := command_data.hooks.get(commands.HookType.POST_INVOKE):
            LOGGER.debug("%s - invoking post-invoke hook", command_data.name)
            await getattr(command, hook_name)(command_instance, context)


class GatewayEnabledClient(Client):
    __slots__ = ("_app",)

    def __init__(self, app: GatewayClientAppT, default_enabled_guilds: t.Sequence[hikari.Snowflakeish] = ()) -> None:
        super().__init__(app.rest, default_enabled_guilds)

        self._app = app

        async def wrap_listener(
            event: hikari.Event,
            *,
            func: t.Callable[..., t.Coroutine[t.Any, t.Any, None]],
            arg_resolver: t.Callable[[hikari.Event], t.Sequence[t.Any]],
        ) -> None:
            return await func(*arg_resolver(event))

        app.event_manager.subscribe(
            hikari.InteractionCreateEvent,
            functools.partial(
                wrap_listener,
                func=self.handle_application_command_interaction,
                arg_resolver=lambda e: [t.cast(hikari.InteractionCreateEvent, e).interaction],
            ),
        )
        app.event_manager.subscribe(
            hikari.StartedEvent,
            functools.partial(wrap_listener, func=self.sync_application_commands, arg_resolver=lambda _: []),
        )


class RestEnabledClient(Client):
    __slots__ = ("_app",)

    def __init__(self, app: RestClientAppT, default_enabled_guilds: t.Sequence[hikari.Snowflakeish] = ()) -> None:
        super().__init__(app.rest, default_enabled_guilds)
        self._app = app
        app.interaction_server.set_listener(hikari.CommandInteraction, self.handle_rest_application_command_interaction)

    async def handle_rest_application_command_interaction(
        self, interaction: hikari.CommandInteraction
    ) -> t.Union[hikari.api.InteractionDeferredBuilder, hikari.api.InteractionMessageBuilder]:  # type: ignore[reportGeneralTypeIssues]
        await super().handle_application_command_interaction(interaction)
        # TODO - intercept context respond calls
