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

__all__ = ["Client", "GatewayEnabledClient", "RestEnabledClient", "client_from_app"]

import asyncio
import collections
import functools
import logging
import typing as t

import hikari

from lightbulb import context as context_
from lightbulb import localization
from lightbulb.commands import commands
from lightbulb.commands import execution
from lightbulb.commands import groups
from lightbulb.internal import constants
from lightbulb.internal import di as di_
from lightbulb.internal import utils

if t.TYPE_CHECKING:
    from lightbulb.commands import options

T = t.TypeVar("T")
CommandOrGroupT = t.TypeVar("CommandOrGroupT", bound=t.Union[groups.Group, t.Type[commands.CommandBase]])
CommandMapT = t.MutableMapping[hikari.Snowflakeish, t.MutableMapping[str, utils.CommandCollection]]
OptionT = t.TypeVar("OptionT", bound=hikari.CommandInteractionOption)

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


class Client:
    """
    Base client implementation supporting generic application command handling.

    Args:
        rest (:obj:`~hikari.api.RESTClient`): The rest client to use.
        default_enabled_guilds (:obj:`~typing.Sequence` [ :obj:`~hikari.Snowflakeish` ]): The guilds that application
            commands should be created in by default. Can be overridden on a per-command basis.
        execution_step_order (:obj:`~typing.Sequence` [ :obj:`~lightbulb.commands.execution.ExecutionStep` ]): The
            order that execution steps will be run in upon command processing.
        default_locale: (:obj:`~hikari.locales.Locale`): The default locale to use for command names and descriptions,
            as well as option names and descriptions. Has no effect if localizations are not being used.
        localization_provider (:obj:`~typing.Callable` [ [ :obj:`str` ], :obj:`~typing.Mapping` [ :obj:`~hikari.locales.Locale`, :obj:`str` ] ]): The
            localization provider function to use. This will be called whenever the client needs to get the
            localizations for a key. Defaults to :obj:`~lightbulb.localization.localization_unsupported` - the client
            does not support localizing commands. **Must** be passed if you intend
            to support localizations.
    """  # noqa: E501

    __slots__ = (
        "rest",
        "default_enabled_guilds",
        "execution_step_order",
        "default_locale",
        "localization_provider",
        "_di",
        "_localization",
        "_commands",
        "_application",
    )

    def __init__(
        self,
        rest: hikari.api.RESTClient,
        default_enabled_guilds: t.Sequence[hikari.Snowflakeish],
        execution_step_order: t.Sequence[execution.ExecutionStep],
        default_locale: hikari.Locale,
        localization_provider: localization.LocalizationProviderT,
    ) -> None:
        super().__init__()

        self.rest = rest
        self.default_enabled_guilds = default_enabled_guilds
        self.execution_step_order = execution_step_order
        self.default_locale = default_locale
        self.localization_provider = localization_provider

        self._di = di_.DependencyInjectionManager()

        self._commands: CommandMapT = collections.defaultdict(lambda: collections.defaultdict(utils.CommandCollection))
        self._application: t.Optional[hikari.PartialApplication] = None

    @property
    def di(self) -> di_.DependencyInjectionManager:
        return self._di

    @t.overload
    def register(
        self, *, guilds: t.Optional[t.Sequence[hikari.Snowflakeish]] = None
    ) -> t.Callable[[CommandOrGroupT], CommandOrGroupT]: ...

    @t.overload
    def register(
        self, command: CommandOrGroupT, *, guilds: t.Optional[t.Sequence[hikari.Snowflakeish]] = None
    ) -> CommandOrGroupT: ...

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

        This method can be used as a function, or a first or second order decorator.

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
                @client.register
                # also valid
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
            register_in = (constants.GLOBAL_COMMAND_KEY,)
        else:
            # commands should either use the passed guilds, or if none passed, use default guilds
            maybe_guilds = guilds or self.default_enabled_guilds
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

        self._application = await self.rest.fetch_application()
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
            if guild_id == constants.GLOBAL_COMMAND_KEY:
                LOGGER.debug("processing global commands")
                # TODO - Do global command syncing
                continue

            LOGGER.debug("processing guild - %s", guild_id)

            builders: t.List[hikari.api.CommandBuilder] = []
            for cmds in guild_commands.values():
                builders.extend(
                    c.as_command_builder(self.default_locale, self.localization_provider)
                    for c in [cmds.slash, cmds.user, cmds.message]
                    if c is not None
                )

            await self.rest.set_application_commands(application, builders, guild_id)

        LOGGER.info("finished syncing commands with discord")

    @staticmethod
    def _get_subcommand(
        options: t.Sequence[OptionT],
    ) -> t.Optional[OptionT]:
        subcommand = filter(
            lambda o: o.type in (hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP), options
        )
        return next(subcommand, None)

    @t.overload
    def _resolve_options_and_command(
        self, interaction: hikari.AutocompleteInteraction
    ) -> t.Optional[t.Tuple[t.Sequence[hikari.AutocompleteInteractionOption], t.Type[commands.CommandBase]]]: ...

    @t.overload
    def _resolve_options_and_command(
        self, interaction: hikari.CommandInteraction
    ) -> t.Optional[t.Tuple[t.Sequence[hikari.CommandInteractionOption], t.Type[commands.CommandBase]]]: ...

    def _resolve_options_and_command(
        self, interaction: t.Union[hikari.AutocompleteInteraction, hikari.CommandInteraction]
    ) -> t.Optional[
        t.Tuple[
            t.Union[t.Sequence[hikari.AutocompleteInteractionOption], t.Sequence[hikari.CommandInteractionOption]],
            t.Type[commands.CommandBase],
        ]
    ]:
        command_path = [interaction.command_name]

        subcommand: t.Union[hikari.CommandInteractionOption, hikari.AutocompleteInteractionOption, None]
        options = interaction.options or []  # TODO - check if this is hikari bug with interaction server
        while (subcommand := self._get_subcommand(options or [])) is not None:
            command_path.append(subcommand.name)
            options = subcommand.options

        root_commands = self._commands.get(interaction.guild_id or constants.GLOBAL_COMMAND_KEY, {}).get(
            interaction.command_name
        )
        if root_commands is None:
            LOGGER.debug("ignoring interaction received for unknown command - %r", interaction.command_name)
            return

        root_command = {
            int(hikari.CommandType.SLASH): root_commands.slash,
            int(hikari.CommandType.USER): root_commands.user,
            int(hikari.CommandType.MESSAGE): root_commands.message,
        }[int(interaction.command_type)]

        if root_command is None:
            LOGGER.debug("ignoring interaction received for unknown command - %r", " ".join(command_path))
            return

        if isinstance(root_command, groups.Group):
            command = root_command.resolve_subcommand(command_path[1:])
            if command is None:
                LOGGER.debug("ignoring interaction received for unknown command - %r", " ".join(command_path))
                return
        else:
            command = root_command

        assert options is not None
        return options, command

    def build_autocomplete_context(
        self,
        interaction: hikari.AutocompleteInteraction,
        options: t.Sequence[hikari.AutocompleteInteractionOption],
        command_cls: t.Type[commands.CommandBase],
    ) -> context_.AutocompleteContext:
        return context_.AutocompleteContext(self, interaction, options, command_cls)

    async def _execute_autocomplete_context(
        self, context: context_.AutocompleteContext, autocomplete_provider: options.AutocompleteProviderT
    ) -> None:
        with di_.ensure_di_context(self.di):
            try:
                await autocomplete_provider(context)
            except Exception as e:
                LOGGER.error(
                    "Error encountered during invocation of autocomplete for command %r",
                    context.command._command_data.qualified_name,
                    exc_info=(type(e), e, e.__traceback__),
                )

    async def handle_autocomplete_interaction(self, interaction: hikari.AutocompleteInteraction) -> None:
        out = self._resolve_options_and_command(interaction)
        if out is None:
            return

        options, command = out

        if not options:
            LOGGER.debug("no options resolved from autocomplete interaction - ignoring")
            return

        context = self.build_autocomplete_context(interaction, options, command)

        option = command._command_data.options.get(context.focused.name, None)
        if option is None or not option.autocomplete:
            LOGGER.debug("interaction appears to refer to option that has autocomplete disabled - ignoring")
            return

        LOGGER.debug("%r - invoking autocomplete", command._command_data.qualified_name)

        assert option.autocomplete_provider is not hikari.UNDEFINED
        await self._execute_autocomplete_context(context, option.autocomplete_provider)

    def build_command_context(
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

    async def _execute_command_context(self, context: context_.Context) -> None:
        with di_.ensure_di_context(self.di):
            try:
                await execution.ExecutionPipeline(context, self.execution_step_order)._run()
            except Exception as e:
                # TODO - dispatch to error handler
                LOGGER.error(
                    "Error encountered during invocation of command %r",
                    context.command._command_data.qualified_name,
                    exc_info=(type(e), e, e.__traceback__),
                )

    async def handle_application_command_interaction(self, interaction: hikari.CommandInteraction) -> None:
        """
        Handle the given command interaction - invoking the correct command.

        Args:
            interaction (:obj:`~hikari.CommandInteraction`): The command interaction to handle.

        Returns:
            :obj:`None`
        """
        out = self._resolve_options_and_command(interaction)
        if out is None:
            return

        options, command = out

        context = self.build_command_context(interaction, options or [], command)

        LOGGER.debug("invoking command - %r", command._command_data.qualified_name)

        await self._execute_command_context(context)

    async def handle_interaction_create(self, interaction: hikari.PartialInteraction) -> None:
        if isinstance(interaction, hikari.AutocompleteInteraction):
            await self.handle_autocomplete_interaction(interaction)
        elif isinstance(interaction, hikari.CommandInteraction):
            await self.handle_application_command_interaction(interaction)


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
                func=self.handle_interaction_create,
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

        app.interaction_server.set_listener(hikari.AutocompleteInteraction, self.handle_rest_autocomplete_interaction)
        app.interaction_server.set_listener(hikari.CommandInteraction, self.handle_rest_application_command_interaction)

        if isinstance(app, hikari.RESTBot):
            app.add_startup_callback(lambda _: self.sync_application_commands())

    def build_rest_autocomplete_context(
        self,
        interaction: hikari.AutocompleteInteraction,
        options: t.Sequence[hikari.AutocompleteInteractionOption],
        command_cls: t.Type[commands.CommandBase],
        response_callback: t.Callable[[hikari.api.InteractionResponseBuilder], None],
    ) -> context_.AutocompleteContext:
        return context_.RestAutocompleteContext(self, interaction, options, command_cls, response_callback)

    async def handle_rest_autocomplete_interaction(
        self, interaction: hikari.AutocompleteInteraction
    ) -> t.AsyncGenerator[hikari.api.InteractionAutocompleteBuilder, t.Any]:
        out = self._resolve_options_and_command(interaction)
        if out is None:
            return

        options, command = out

        if not options:
            LOGGER.debug("no options resolved from autocomplete interaction - ignoring")
            return

        initial_response_ready = asyncio.Event()
        initial_response: t.Optional[hikari.api.InteractionResponseBuilder] = None

        def set_response(response: hikari.api.InteractionResponseBuilder) -> None:
            nonlocal initial_response, initial_response_ready
            initial_response = response
            initial_response_ready.set()

        context = self.build_rest_autocomplete_context(interaction, options, command, set_response)

        option = command._command_data.options.get(context.focused.name, None)
        if option is None or not option.autocomplete:
            LOGGER.debug("interaction appears to refer to option that has autocomplete disabled - ignoring")
            return

        LOGGER.debug("%r - invoking autocomplete", command._command_data.qualified_name)

        assert option.autocomplete_provider is not hikari.UNDEFINED
        task = asyncio.create_task(self._execute_autocomplete_context(context, option.autocomplete_provider))
        try:
            await asyncio.wait_for(initial_response_ready.wait(), timeout=5)

            if initial_response is not None:
                yield initial_response
        except asyncio.TimeoutError:
            LOGGER.warning(
                "Autocomplete for command %r took too long to create initial response",
                command._command_data.qualified_name,
            )

        # Ensure the autocomplete provider completes
        await task

    def build_rest_command_context(
        self,
        interaction: hikari.CommandInteraction,
        options: t.Sequence[hikari.CommandInteractionOption],
        command_cls: t.Type[commands.CommandBase],
        response_callback: t.Callable[[hikari.api.InteractionResponseBuilder], None],
    ) -> context_.Context:
        return context_.RestContext(self, interaction, options, command_cls(), response_callback)

    async def handle_rest_application_command_interaction(
        self, interaction: hikari.CommandInteraction
    ) -> t.AsyncGenerator[
        t.Union[
            hikari.api.InteractionDeferredBuilder,
            hikari.api.InteractionMessageBuilder,
            hikari.api.InteractionModalBuilder,
        ],
        t.Any,
    ]:
        out = self._resolve_options_and_command(interaction)
        if out is None:
            return

        options, command = out

        initial_response_ready = asyncio.Event()
        initial_response: t.Optional[hikari.api.InteractionResponseBuilder] = None

        def set_response(response: hikari.api.InteractionResponseBuilder) -> None:
            nonlocal initial_response, initial_response_ready

            initial_response = response
            initial_response_ready.set()

        context = self.build_rest_command_context(interaction, options or [], command, set_response)
        LOGGER.debug("invoking command - %r", command._command_data.qualified_name)

        task = asyncio.create_task(self._execute_command_context(context))
        try:
            await asyncio.wait_for(initial_response_ready.wait(), timeout=5)

            if initial_response is not None:
                yield initial_response
        except asyncio.TimeoutError as e:
            LOGGER.warning(
                "Command %r took too long to create initial response",
                command._command_data.qualified_name,
                exc_info=(type(e), e, e.__traceback__),
            )

        # Ensure the command completes
        await task


def client_from_app(
    app: t.Union[GatewayClientAppT, RestClientAppT],
    default_enabled_guilds: t.Sequence[hikari.Snowflakeish] = (constants.GLOBAL_COMMAND_KEY,),
    execution_step_order: t.Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
    default_locale: hikari.Locale = hikari.Locale.EN_US,
    localization_provider: localization.LocalizationProviderT = localization.localization_unsupported,
) -> Client:
    """
    Create and return the appropriate client implementation from the given application.

    Args:
        app: Application that either supports gateway events, or an interaction server.
        default_enabled_guilds (:obj:`~typing.Sequence` [ :obj:`~hikari.Snowflakeish` ]): The guilds that application
            commands should be created in by default.
        execution_step_order (:obj:`~typing.Sequence` [ :obj:`~lightbulb.commands.execution.ExecutionStep` ]): The
            order that execution steps will be run in upon command processing.
        default_locale: (:obj:`~hikari.locales.Locale`): The default locale to use for command names and descriptions,
            as well as option names and descriptions. Has no effect if localizations are not being used.
            Defaults to :obj:`hikari.locales.Locale.EN_US`.
        localization_provider (:obj:`~typing.Callable` [ [ :obj:`str` ], :obj:`~typing.Mapping` [ :obj:`~hikari.locales.Locale`, :obj:`str` ] ]): The
            localization provider function to use. This will be called whenever the client needs to get the
            localizations for a key. Defaults to :obj:`~lightbulb.localization.localization_unsupported` - the client
            does not support localizing commands. **Must** be passed if you intend
            to support localizations.

    Returns:
        :obj:`~Client`: The created client instance.
    """  # noqa: E501
    if isinstance(app, GatewayClientAppT):
        LOGGER.debug("building gateway client from app")
        cls = GatewayEnabledClient
    else:
        LOGGER.debug("building REST client from app")
        cls = RestEnabledClient

    return cls(app, default_enabled_guilds, execution_step_order, default_locale, localization_provider)  # type: ignore[reportArgumentType]
