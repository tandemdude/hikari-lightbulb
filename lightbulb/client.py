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
import collections
import functools
import logging
import typing as t

import hikari
import svcs

from lightbulb import context as context_
from lightbulb.commands import commands
from lightbulb.commands import execution
from lightbulb.commands import groups
from lightbulb.internal import di
from lightbulb.internal import utils

__all__ = ["Client", "GatewayEnabledClient", "RestEnabledClient", "client_from_app"]

T = t.TypeVar("T")
CommandOrGroupT = t.TypeVar("CommandOrGroupT", bound=t.Union[groups.Group, t.Type[commands.CommandBase]])
CommandMapT = t.MutableMapping[hikari.Snowflakeish, t.MutableMapping[str, utils.CommandCollection]]

GLOBAL_COMMAND_KEY = 0
DEFAULT_EXECUTION_STEP_ORDER = (
    execution.ExecutionSteps.MAX_CONCURRENCY,
    execution.ExecutionSteps.CHECKS,
    execution.ExecutionSteps.COOLDOWNS,
)
LOGGER = logging.getLogger("lightbulb.client")


@t.runtime_checkable
class GatewayClientAppT(hikari.EventManagerAware, hikari.RESTAware, t.Protocol):
    ...


@t.runtime_checkable
class RestClientAppT(hikari.InteractionServerAware, hikari.RESTAware, t.Protocol):
    ...


class Client(abc.ABC):
    __slots__ = (
        "_commands",
        "_rest",
        "_default_enabled_guilds",
        "_execution_step_order",
        "_application",
        "_di_registry",
        "__di_container",
    )

    def __init__(
        self,
        rest: hikari.api.RESTClient,
        default_enabled_guilds: t.Sequence[hikari.Snowflakeish],
        execution_step_order: t.Sequence[execution.ExecutionStep],
    ) -> None:
        self._rest: hikari.api.RESTClient = rest
        self._default_enabled_guilds = default_enabled_guilds
        self._execution_step_order = execution_step_order

        self._commands: CommandMapT = collections.defaultdict(lambda: collections.defaultdict(utils.CommandCollection))
        self._application: t.Optional[hikari.PartialApplication] = None

        self._di_registry: svcs.Registry = svcs.Registry()
        self.__di_container: t.Optional[svcs.Container] = None

    @property
    def _di_container(self) -> svcs.Container:
        if self.__di_container is None:
            self.__di_container = svcs.Container(self._di_registry)
        return self.__di_container

    def register_dependency(self, type: t.Type[T], factory: t.Callable[[], t.Union[t.Awaitable[T], T]]) -> None:
        self._di_registry.register_factory(type, factory)  # type: ignore[reportUnknownMemberType]

    @t.overload
    def register(
        self, guilds: t.Optional[t.Sequence[hikari.Snowflakeish]] = None
    ) -> t.Callable[[CommandOrGroupT], CommandOrGroupT]:
        ...

    @t.overload
    def register(
        self, guilds: t.Optional[t.Sequence[hikari.Snowflakeish]], command_or_group: CommandOrGroupT
    ) -> CommandOrGroupT:
        ...

    def register(
        self,
        guilds: t.Optional[t.Sequence[hikari.Snowflakeish]] = None,
        command_or_group: t.Optional[CommandOrGroupT] = None,
    ) -> t.Union[CommandOrGroupT, t.Callable[[CommandOrGroupT], CommandOrGroupT]]:
        register_in: t.Sequence[hikari.Snowflakeish]
        if not guilds and guilds is not None:
            # commands should ignore default guilds and be global
            register_in = (GLOBAL_COMMAND_KEY,)
        else:
            # commands should either use the passed guilds, or if none passed, use default guilds
            maybe_guilds = guilds or self._default_enabled_guilds
            # pyright isn't happy about just using the above line even though it should be fine,
            # so added the below just to remove the error
            register_in = maybe_guilds if maybe_guilds is not hikari.UNDEFINED else ()

        # Used as a function
        if command_or_group is not None:
            name = (
                command_or_group.name
                if isinstance(command_or_group, groups.Group)
                else command_or_group._.command_data.name
            )

            for guild_id in register_in:
                self._commands[guild_id][name].put(command_or_group)

            LOGGER.debug("command %s registered successfully", name)
            return command_or_group

        # Used as a decorator
        def _inner(command_or_group_: CommandOrGroupT) -> CommandOrGroupT:
            return self.register(guilds, command_or_group_)

        return _inner

    async def _ensure_application(self) -> hikari.PartialApplication:
        if self._application is not None:
            return self._application

        self._application = await self._rest.fetch_application()
        return self._application

    async def sync_application_commands(self) -> None:
        # TODO - implement syncing logic - for now just do create
        LOGGER.info("syncing commands with discord")
        application = await self._ensure_application()

        for guild_id, guild_commands in self._commands.items():
            if guild_id == GLOBAL_COMMAND_KEY:
                LOGGER.debug("processing global commands")
                # TODO - Do global command syncing
                continue

            LOGGER.debug("processing guild - %s", guild_id)

            builders: t.List[hikari.api.CommandBuilder] = []
            for cmds in guild_commands.values():
                builders.extend(c.as_command_builder() for c in [cmds.slash, cmds.user, cmds.message] if c is not None)

            await self._rest.set_application_commands(application, builders, guild_id)

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

        root_commands = self._commands.get(interaction.guild_id or GLOBAL_COMMAND_KEY, {}).get(interaction.command_name)
        if root_commands is None:
            LOGGER.debug("ignoring interaction create received for unknown command - %s", interaction.command_name)
            return

        root_command = {
            int(hikari.CommandType.SLASH): root_commands.slash,
            int(hikari.CommandType.USER): root_commands.user,
            int(hikari.CommandType.MESSAGE): root_commands.message,
        }[int(interaction.command_type)]

        if root_command is None:
            LOGGER.debug("ignoring interaction create received for unknown command - %s", " ".join(command_path))
            return

        if isinstance(root_command, groups.Group):
            command = root_command.resolve_subcommand(command_path[1:])
            if command is None:
                LOGGER.debug("ignoring interaction create received for unknown command - %s", " ".join(command_path))
                return
        else:
            command = root_command

        command_instance = command()
        context = self.build_context(interaction, options or [], command_instance)
        command_instance._set_context(context)

        LOGGER.debug("%s - invoking command", command._.command_data.name)

        token = di._di_container.set(self._di_container)
        try:
            await execution.ExecutionPipeline(context, self._execution_step_order)._run()
        except Exception as e:
            # TODO - dispatch to error handler
            LOGGER.error("Error during command invocation", exc_info=(type(e), e, e.__traceback__))
        finally:
            di._di_container.reset(token)


class GatewayEnabledClient(Client):
    __slots__ = ("_app",)

    def __init__(self, app: GatewayClientAppT, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(app.rest, *args, **kwargs)
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
                arg_resolver=lambda e: (t.cast(hikari.InteractionCreateEvent, e).interaction,),
            ),
        )
        app.event_manager.subscribe(
            hikari.StartedEvent,
            functools.partial(wrap_listener, func=self.sync_application_commands, arg_resolver=lambda _: ()),
        )


class RestEnabledClient(Client):
    __slots__ = ("_app",)

    def __init__(self, app: RestClientAppT, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(app.rest, *args, **kwargs)
        self._app = app

        app.interaction_server.set_listener(hikari.CommandInteraction, self.handle_rest_application_command_interaction)

    async def handle_rest_application_command_interaction(
        self, interaction: hikari.CommandInteraction
    ) -> t.Union[hikari.api.InteractionDeferredBuilder, hikari.api.InteractionMessageBuilder]:  # type: ignore[reportGeneralTypeIssues]
        await super().handle_application_command_interaction(interaction)
        # TODO - intercept context respond calls


def client_from_app(
    app: t.Union[GatewayClientAppT, RestClientAppT],
    default_enabled_guilds: t.Sequence[hikari.Snowflakeish] = (GLOBAL_COMMAND_KEY,),
    execution_step_order: t.Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
) -> Client:
    if isinstance(app, GatewayClientAppT):
        LOGGER.debug("building gateway client from app")
        return GatewayEnabledClient(app, default_enabled_guilds, execution_step_order)

    LOGGER.debug("building REST client from app")
    return RestEnabledClient(app, default_enabled_guilds, execution_step_order)
