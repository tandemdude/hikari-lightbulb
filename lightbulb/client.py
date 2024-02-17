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
    """Protocol indicating an application supports gateway events."""


@t.runtime_checkable
class RestClientAppT(hikari.InteractionServerAware, hikari.RESTAware, t.Protocol):
    """Protocol indicating an application supports an interaction server."""


class Client(abc.ABC):
    """
    Base client implementation supporting generic application command handling.

    Args:
        rest (:obj:`~hikari.api.RESTClient`): The rest client to use.
        default_enabled_guilds (:obj:`~typing.Sequence` [ :obj:`~hikari.Snowflakeish` ]): The guilds that application
            commands should be created in by default. Can be overridden on a per-command basis.
        execution_step_order (:obj:`~typing.Sequence` [ :obj:`~lightbulb.commands.execution.ExecutionStep` ]): The
            order that execution steps will be run in upon command processing.
    """

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
        """The dependency injection container to use for this instance. Lazily instantiated."""
        if self.__di_container is None:
            self.__di_container = svcs.Container(self._di_registry)
        return self.__di_container

    def register_dependency(self, type: t.Type[T], factory: t.Callable[[], t.Union[t.Awaitable[T], T]]) -> None:
        """
        Register a dependency as usable by dependency injection. All dependencies are considered to be
        singletons, meaning the factory will always be called at most once.

        Args:
            type (:obj:`~typing.Type` [ ``T`` ]): The type of the dependency to register.
            factory: The factory function to use to provide the dependency value.

        Returns:
            :obj:`None`
        """
        self._di_registry.register_factory(type, factory)  # type: ignore[reportUnknownMemberType]

    @t.overload
    def register(
        self, *, guilds: t.Optional[t.Sequence[hikari.Snowflakeish]] = None
    ) -> t.Callable[[CommandOrGroupT], CommandOrGroupT]:
        ...

    @t.overload
    def register(
        self, command: CommandOrGroupT, *, guilds: t.Optional[t.Sequence[hikari.Snowflakeish]] = None
    ) -> CommandOrGroupT:
        ...

    def register(
        self,
        command: t.Optional[CommandOrGroupT] = None,
        *,
        guilds: t.Optional[t.Sequence[hikari.Snowflakeish]] = None,
    ) -> t.Union[CommandOrGroupT, t.Callable[[CommandOrGroupT], CommandOrGroupT]]:
        """
        Register a command or group with this client instance. Optionally, a sequence of guild ids can
        be provided to make the commands created in specific guilds only - overriding the value for
        default enabled guilds.

        This method can be used as a function or a second order decorator.

        Args:
            command (:obj:`~typing.Union` [ :obj:`~typing.Type` [ :obj:`~lightbulb.commands.commands.CommandBase ], :obj:`~lightbulb.commands.groups.Group` ]): The
                command class or command group to register with the client.
            guilds (:obj:`~typing.Optional` [ :obj:`~typing.Sequence` [ :obj:`~hikari.Snowflakeish` ]]): The guilds
                to create the command or group in. If set to :obj:`None`, then this will fall back to the default
                enabled guilds. To override default enabled guilds and make the command or group global, this should
                be set to an empty sequence.

        Returns:
            The registered command or group, unchanged.

        Example:

            .. code-block:: python

                client = lightbulb.client_from_app(...)

                # valid
                @client.register(guilds=[...])
                class Example(
                    lightbulb.SlashCommand,
                    ...
                ):
                    ...

                # also valid
                client.register(Example, guilds=[...])
        """  # noqa: E501
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
        if command is not None:
            name = command.name if isinstance(command, groups.Group) else command._command_data.name

            for guild_id in register_in:
                self._commands[guild_id][name].put(command)

            LOGGER.debug("command %r (%r) registered successfully", name, command)
            return command

        # Used as a decorator
        def _inner(command_: CommandOrGroupT) -> CommandOrGroupT:
            return self.register(command_, guilds=register_in)

        return _inner

    async def _ensure_application(self) -> hikari.PartialApplication:
        if self._application is not None:
            return self._application

        self._application = await self._rest.fetch_application()
        return self._application

    async def sync_application_commands(self) -> None:
        """
        Sync all application commands registered to the bot with discord.

        Returns:
            :obj:`None`
        """
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
        command_cls: t.Type[commands.CommandBase],
    ) -> context_.Context:
        """
        Build a context object from the given parameters.

        Args:
            interaction (:obj:`~hikari.CommandInteraction`): The interaction for the command invocation.
            options (:obj:`~typing.Sequence` [ :obj:`hikari.CommandInteractionOption` ]): The options to use to
                invoke the command with.
            command_cls (:obj:`~typing.Type` [ :obj:`~lightbulb.commands.commands.CommandBase` ]): The command class
                that represents the command that should be invoked for the interaction.

        Returns:
            :obj:`~lightbulb.context.Context`: The built context.
        """
        return context_.Context(
            client=self,
            interaction=interaction,
            options=options,
            command=command_cls(),
        )

    async def handle_application_command_interaction(self, interaction: hikari.CommandInteraction) -> None:
        """
        Handle the given command interaction - invoking the correct command.

        Args:
            interaction (:obj:`~hikari.CommandInteraction`): The command interaction to handle.

        Returns:
            :obj:`None`
        """
        # Just to double-check
        if not isinstance(interaction, hikari.CommandInteraction):  # type: ignore[reportUnnecessaryIsInstance]
            return

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

        context = self.build_context(interaction, options or [], command)

        LOGGER.debug("%r - invoking command", " ".join(command_path))

        with di.ensure_di_context(self):
            try:
                await execution.ExecutionPipeline(context, self._execution_step_order)._run()
            except Exception as e:
                # TODO - dispatch to error handler
                LOGGER.error(
                    "Error encountered during invocation of command %r",
                    " ".join(command_path),
                    exc_info=(type(e), e, e.__traceback__),
                )


class GatewayEnabledClient(Client):
    """
    Client implementation for applications that support gateway events.

    Warning:
        This client should not be instantiated manually. Use :func:`~client_from_app` instead.
    """

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
    """
    Client implementation for applications that support an interaction server.

    Warning:
        This client should not be instantiated manually. Use :func:`~client_from_app` instead.
    """

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
    """
    Create and return the appropriate client implementation from the given application.

    Args:
        app: Application that either supports gateway events, or an interaction server.
        default_enabled_guilds (:obj:`~typing.Sequence` [ :obj:`~hikari.Snowflakeish` ]): The guilds that application
            commands should be created in by default.
        execution_step_order (:obj:`~typing.Sequence` [ :obj:`~lightbulb.commands.execution.ExecutionStep` ]): The
            order that execution steps will be run in upon command processing.

    Returns:
        :obj:`~Client`: The created client instance.
    """
    if isinstance(app, GatewayClientAppT):
        LOGGER.debug("building gateway client from app")
        return GatewayEnabledClient(app, default_enabled_guilds, execution_step_order)

    LOGGER.debug("building REST client from app")
    return RestEnabledClient(app, default_enabled_guilds, execution_step_order)
