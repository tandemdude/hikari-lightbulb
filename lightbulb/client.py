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

__all__ = ["DEFAULT_EXECUTION_STEP_ORDER", "Client", "GatewayEnabledClient", "RestEnabledClient", "client_from_app"]

import abc
import asyncio
import collections
import functools
import importlib
import logging
import pathlib
import sys
import typing as t

import hikari

from lightbulb import context as context_
from lightbulb import di as di_
from lightbulb import exceptions
from lightbulb import loaders
from lightbulb import localization
from lightbulb import tasks
from lightbulb import utils
from lightbulb.commands import commands
from lightbulb.commands import execution
from lightbulb.commands import groups
from lightbulb.internal import constants
from lightbulb.internal import sync
from lightbulb.internal import utils as i_utils

if t.TYPE_CHECKING:
    import types

    from lightbulb.commands import options as options_
    from lightbulb.internal.types import MaybeAwaitable

T = t.TypeVar("T")
CommandMap: t.TypeAlias = t.MutableMapping[hikari.Snowflakeish, t.MutableMapping[str, i_utils.CommandCollection]]
CommandOrGroup: t.TypeAlias = t.Union[groups.Group, type[commands.CommandBase]]
CommandOrGroupT = t.TypeVar("CommandOrGroupT", bound=CommandOrGroup)
ErrorHandler: t.TypeAlias = t.Callable[
    "t.Concatenate[exceptions.ExecutionPipelineFailedException, ...]", t.Awaitable[bool]
]
ErrorHandlerT = t.TypeVar("ErrorHandlerT", bound=ErrorHandler)
OptionT = t.TypeVar("OptionT", bound=hikari.CommandInteractionOption)

LOGGER = logging.getLogger(__name__)
DEFAULT_EXECUTION_STEP_ORDER = (
    execution.ExecutionSteps.MAX_CONCURRENCY,
    execution.ExecutionSteps.CHECKS,
    execution.ExecutionSteps.COOLDOWNS,
    execution.ExecutionSteps.PRE_INVOKE,
    execution.ExecutionSteps.INVOKE,
    execution.ExecutionSteps.POST_INVOKE,
)
"""The order that execution steps will be run in if you don't specify your own order."""


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
        rest: The rest client to use.
        default_enabled_guilds: The guilds that application commands should be created in by default.
            Can be overridden on a per-command basis.
        execution_step_order: The order that execution steps will be run in upon command processing.
        default_locale: The default locale to use for command names and descriptions,
            as well as option names and descriptions. Has no effect if localizations are not being used.
        localization_provider: The localization provider function to use. This will be called whenever the client
            needs to get the localizations for a key.
        delete_unknown_commands: Whether to delete existing commands that the client does not have
            an implementation for during command syncing.
        deferred_registration_callback: The callback to use to resolve which guilds a command should be created in
            if a command is registered using :meth:`~Client.register_deferred`. Allows for commands to be
            dynamically created in guilds, for example enabled on a per-guild basis using feature flags.
    """

    __slots__ = (
        "rest",
        "default_enabled_guilds",
        "execution_step_order",
        "default_locale",
        "localization_provider",
        "delete_unknown_commands",
        "deferred_registration_callback",
        "_di",
        "_localization",
        "_localized_commands",
        "_deferred_commands",
        "_commands",
        "_error_handlers",
        "_application",
        "_extensions",
        "_tasks",
        "_started",
    )

    def __init__(
        self,
        rest: hikari.api.RESTClient,
        default_enabled_guilds: t.Sequence[hikari.Snowflakeish],
        execution_step_order: t.Sequence[execution.ExecutionStep],
        default_locale: hikari.Locale,
        localization_provider: localization.LocalizationProviderT,
        delete_unknown_commands: bool,
        deferred_registration_callback: t.Callable[
            [CommandOrGroup], MaybeAwaitable[hikari.Snowflakeish | t.Sequence[hikari.Snowflakeish]]
        ]
        | None,
    ) -> None:
        super().__init__()

        self.rest = rest
        self.default_enabled_guilds = default_enabled_guilds
        self.execution_step_order = execution_step_order
        self.default_locale = default_locale
        self.localization_provider = localization_provider
        self.delete_unknown_commands = delete_unknown_commands
        self.deferred_registration_callback = deferred_registration_callback

        self._di = di_.DependencyInjectionManager()

        self._localized_commands: list[tuple[t.Sequence[hikari.Snowflakeish], CommandOrGroup]] = []
        self._deferred_commands: list[CommandOrGroup] = []

        self._commands: CommandMap = collections.defaultdict(lambda: collections.defaultdict(i_utils.CommandCollection))
        self._error_handlers: dict[int, list[ErrorHandler]] = {}
        self._application: t.Optional[hikari.PartialApplication] = None
        self._extensions: set[str] = set()
        self._tasks: set[tasks.Task] = set()

        self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.api.RESTClient, self.rest)
        self.di.registry_for(di_.Contexts.DEFAULT).register_value(Client, self)

        self._started = False

    @property
    @abc.abstractmethod
    def app(self) -> hikari.RESTAware:
        """The app that this client was created from."""

    @property
    def di(self) -> di_.DependencyInjectionManager:
        """The dependency injection manager used by this client."""
        return self._di

    async def start(self, *_: t.Any) -> None:
        """
        Starts the client. Ensures that commands are registered properly with the client, and that
        commands have been synced with discord. Also starts any tasks that were created with `auto_start` set to
        :obj:`True`.

        Returns:
            :obj:`None`

        Raises:
            :obj:`RuntimeError`: If the client has already been started.
        """
        if self._started:
            raise RuntimeError("cannot start already-started client")

        await self.sync_application_commands()
        self._started = True

        for task in self._tasks:
            if task._auto_start:
                task.start()

    async def stop(self, *_: t.Any) -> None:
        """
        Stops the client. Cancelling any tasks that are running, and closing the default DI container - causing teardown
        methods to be called.

        Returns:
            :obj:`None`
        """
        if not self._started:
            return

        for task in self._tasks:
            task.cancel()

        await self.di.close()

    @t.overload
    def task(
        self, trigger: tasks.Trigger, /, auto_start: bool = True, max_failures: int = 1, max_invocations: int = -1
    ) -> t.Callable[[tasks.TaskFunc], tasks.Task]: ...
    @t.overload
    def task(self, task_: tasks.Task, /) -> tasks.Task: ...

    def task(  # noqa: D417
        self,
        task_or_trigger: tasks.Trigger | tasks.Task,
        /,
        auto_start: bool = True,
        max_failures: int = 1,
        max_invocations: int = -1,
    ) -> t.Callable[[tasks.TaskFunc], tasks.Task] | tasks.Task:
        """
        Second order decorator to register a repeating task with the client. Task functions will have
        dependency injection enabled on them automatically. Task functions **must** be asynchronous.

        Args:
            trigger: The trigger function to use to resolve the interval between task executions.
            auto_start: Whether the task should be started automatically. This means that if the task is added to
                the client upon the client being started, the task will also be started; it will also be started
                if being added to an already-started client.
            max_failures: The maximum number of failed attempts to execute the task before it is cancelled.
            max_invocations: The maximum number of times the task can be invoked before being stopped.

        Note:
            This method can also be called with an existing task object to register it directly.

        Example:

            .. code-block:: python

                @client.task(lightbulb.uniformtrigger(minutes=1)
                async def print_hi() -> None:
                    print("HI")
        """
        if isinstance(task_or_trigger, tasks.Task):
            task_obj = task_or_trigger

            if task_obj in self._tasks:
                return task_obj

            task_obj._client = self

            self._tasks.add(task_obj)
            if self._started and task_obj._auto_start:
                task_obj.start()

            return task_obj

        def _inner(func: tasks.TaskFunc) -> tasks.Task:
            task_obj = tasks.Task(func, task_or_trigger, auto_start, max_failures, max_invocations)
            return self.task(task_obj)

        return _inner

    def remove_task(self, task: tasks.Task, cancel: bool = False) -> None:
        """
        Remove a task from the client. Tasks will be stopped and unregistered from the client once they complete.

        Args:
            task: The task to remove from the client.
            cancel: Whether the task should be immediately cancelled instead of stopped gracefully.

        Returns:
            :obj:`None`
        """
        if task.running:
            assert task._task is not None
            task._task.add_done_callback(lambda _: setattr(task, "_client", None))

            if cancel:
                task.cancel()
            else:
                task.stop()
        else:
            task._client = None

        self._tasks.remove(task)

    @t.overload
    def error_handler(self, *, priority: int = 0) -> t.Callable[[ErrorHandlerT], ErrorHandlerT]: ...

    @t.overload
    def error_handler(self, func: ErrorHandlerT, *, priority: int = 0) -> ErrorHandlerT: ...

    def error_handler(
        self, func: ErrorHandlerT | None = None, *, priority: int = 0
    ) -> ErrorHandlerT | t.Callable[[ErrorHandlerT], ErrorHandlerT]:
        """
        Register an error handler function to call when an :obj:`~lightbulb.commands.execution.ExecutionPipeline` fails.
        Also enables dependency injection for the error handler function.

        The function must take the exception as its first argument, which will be an instance of
        :obj:`~lightbulb.exceptions.ExecutionPipelineFailedException`. The function **must** return a boolean
        indicating whether the exception was successfully handled. Non-boolean return values will be cast to booleans.

        Args:
            func: The function to register as a command error handler.
            priority: The priority that this handler should be registered at. Higher priority handlers
                will be executed first.
        """
        if func is not None:
            wrapped = di_.with_di(func)

            handlers_with_same_priority = self._error_handlers.get(priority, [])
            handlers_with_same_priority.append(wrapped)
            self._error_handlers[priority] = handlers_with_same_priority

            sorted_handlers = sorted(self._error_handlers.items(), key=lambda item: item[0], reverse=True)
            self._error_handlers = {k: v for k, v in sorted_handlers}

            return wrapped

        def _inner(func_: ErrorHandlerT) -> ErrorHandlerT:
            return self.error_handler(func_, priority=priority)

        return _inner

    def remove_error_handler(self, func: ErrorHandler) -> None:
        """
        Unregister a command error handler function from the client.

        Args:
            func: The function to unregister as a command error handler.

        Returns:
            :obj:`None`
        """
        new_handlers: dict[int, list[ErrorHandler]] = {}
        for priority, handlers in self._error_handlers.items():
            handlers = [
                h for h in handlers if h is not func and (isinstance(h, di_.AutoInjecting) and h._func is not func)
            ]
            if handlers:
                new_handlers[priority] = t.cast(list[ErrorHandler], handlers)

        sorted_handlers = sorted(new_handlers.items(), key=lambda item: item[0], reverse=True)
        self._error_handlers = {k: v for k, v in sorted_handlers}

    @t.overload
    def register(
        self, *, guilds: t.Sequence[hikari.Snowflakeish] | None = None
    ) -> t.Callable[[CommandOrGroupT], CommandOrGroupT]: ...

    @t.overload
    def register(
        self, command: CommandOrGroupT, *, guilds: t.Sequence[hikari.Snowflakeish] | None = None
    ) -> CommandOrGroupT: ...

    def register(
        self,
        command: CommandOrGroupT | None = None,
        *,
        guilds: t.Sequence[hikari.Snowflakeish] | None = None,
    ) -> CommandOrGroupT | t.Callable[[CommandOrGroupT], CommandOrGroupT]:
        """
        Register a command or group with this client instance. Optionally, a sequence of guild ids can
        be provided to make the commands created in specific guilds only - overriding the value for
        default enabled guilds.

        This method can be used as a function, or a first or second order decorator.

        Args:
            command: The command class or command group to register with the client.
            guilds: The guilds to create the command or group in. If set to :obj:`None`, then this will
                fall back to the default enabled guilds. To override default enabled guilds and make the
                command or group global, this should be set to an empty sequence.

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
        """
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

        # Used as a function or first-order decorator
        if command is not None:
            name = command.name if isinstance(command, groups.Group) else command._command_data.name
            localize = command.localize if isinstance(command, groups.Group) else command._command_data.localize

            if localize:
                # We need to handle localized commands separately because we don't know what their
                # name is until we resolve it using the callback
                self._localized_commands.append((register_in, command))
            else:
                for guild_id in register_in:
                    self._commands[guild_id][name].put(command)

            LOGGER.debug("command %r (%r) registered successfully", name, command)
            return command

        # Used as a second-order decorator
        def _inner(command_: CommandOrGroupT) -> CommandOrGroupT:
            return self.register(command_, guilds=register_in)

        return _inner

    def register_deferred(self, command: CommandOrGroupT) -> CommandOrGroupT:
        """
        Register a command with the client, but defer resolving the guilds that the command should be created
        in until the client has been started.

        Args:
            command: The command class or command group to register with the client.

        Returns:
            The registered command or group, unchanged.

        Raises:
            :obj:`ValueError`: If no ``deferred_registration_callback`` was set upon client creation.
        """
        if self.deferred_registration_callback is None:
            raise ValueError("cannot defer registration if no deferred registration callback was provided")

        self._deferred_commands.append(command)
        return command

    def unregister(self, command: CommandOrGroup) -> None:
        """
        Unregister a command with the client. This will prevent the client from handling any incoming
        interactions for the given command globally, or in any guild. This **will not** delete the command from
        discord and users will still be able to see it in the command menu.

        Args:
            command: The command class or command group to unregister with the client.

        Returns:
            :obj:`None`
        """
        for mapping in self._commands.values():
            for collection in mapping.values():
                collection.remove(command)

        self._deferred_commands = [cmd for cmd in self._deferred_commands if cmd is not command]
        localized_commands = [item for item in self._localized_commands if item[1] is not command]
        self._localized_commands = localized_commands

    async def load_extensions(self, *import_paths: str) -> None:
        """
        Load extensions from the given import paths. If loading of a single extension fails it will be skipped
        and any loaders already processed, as well as the one that caused the error will be removed.

        Args:
            *import_paths: The import paths for the extensions to be loaded.

        Returns:
            :obj:`None`

        See Also:
            :meth:`~Client.load_extensions_from_package`
        """
        for path in import_paths:
            if path in self._extensions:
                LOGGER.warning("extension %r is already loaded - skipping", path)
                continue

            try:
                extension = importlib.import_module(path)
            except ImportError as e:
                LOGGER.error("error importing extension %r - skipping", path, exc_info=(type(e), e, e.__traceback__))
                continue

            loaded: list[loaders.Loader] = []

            maybe_loader: loaders.Loader | None = None
            try:
                for name in dir(extension):
                    if isinstance(item := getattr(extension, name, None), loaders.Loader) and item not in loaded:
                        maybe_loader = item
                        await maybe_loader.add_to_client(self)

                        loaded.append(maybe_loader)
            except Exception as e:
                LOGGER.error("error loading extension %r - skipping", path, exc_info=(type(e), e, e.__traceback__))

                if maybe_loader is not None and maybe_loader not in loaded:
                    loaded.append(maybe_loader)

                for loader in loaded:
                    await loader.remove_from_client(self)

                # Remove the errored extension from sys.modules so that when it is fixed,
                # the extension will be able to be loaded as normal.
                del sys.modules[path]

                continue

            if not loaded:
                LOGGER.warning("found no loaders in extension %r - skipping", path)
                continue

            self._extensions.add(path)
            LOGGER.info("extension %r loaded successfully", path)

    async def load_extensions_from_package(self, package: types.ModuleType, *, recursive: bool = False) -> None:
        """
        Load all extension modules from the given package. Ignores any files with a name that starts with an underscore.

        Args:
            package: The package to load extensions from. Expects the imported module for
                the ``__init__.py`` file in the package.
            recursive: Whether to recursively load extensions from subpackages. Defaults to :obj:`False`.

        Returns:
            :obj:`None`

        Raises:
            :obj:`TypeError`: If the given module is not for the ``__init__.py`` file of a package.

        Example:

            Given the following file structure:

            .. code-block:: bash

                extensions/
                ├── __init__.py
                ├── extension1.py
                └── extension2.py
                bot.py

            To load all extensions in the ``extensions`` package you should do the following:

            .. code-block:: python

                import extensions

                await client.load_extensions_from_package(extensions)

        See Also:
            :meth:`~Client.load_extensions`
        """
        if not (package.__file__ or "").endswith("__init__.py"):
            raise TypeError(f"the given module does not appear to be a package: {package.__name__}")

        assert package.__file__ is not None
        package_path = pathlib.Path(package.__file__).parent
        package_import_path = package.__name__

        extensions: list[str] = []
        for item in package_path.iterdir():
            if item.is_dir():
                if not recursive:
                    continue

                if not (item / "__init__.py").exists():
                    continue

                next_package = importlib.import_module(package_import_path + "." + item.name)
                await self.load_extensions_from_package(next_package, recursive=recursive)

            if item.name.startswith("_") or not item.name.endswith(".py"):
                continue

            extensions.append(package_import_path + "." + item.name[:-3])

        await self.load_extensions(*extensions)

    async def unload_extensions(self, *import_paths: str) -> None:
        """
        Unload extensions from the given import paths. If unloading of a single extension fails an error will be
        raised and no further extensions will be unloaded. Attempting to unload an extensions that is not loaded will
        log a warning and continue with the remaining extensions.

        Args:
            *import_paths: The import paths for the extensions to be unloaded.

        Returns:
            :obj:`None`

        Raises:
            When an exception is thrown during removing loaders from the client for the extension being unloaded.
        """
        for path in import_paths:
            extension = sys.modules.get(path)
            if extension is None or path not in self._extensions:
                LOGGER.warning("extension %r is not loaded - skipping", path)
                continue

            to_unload: list[loaders.Loader] = []
            for name in dir(extension):
                if isinstance(item := getattr(extension, name, None), loaders.Loader) and item not in to_unload:
                    to_unload.append(item)

            for loaded in to_unload:
                await loaded.remove_from_client(self)

            del sys.modules[path]
            self._extensions.remove(path)
            LOGGER.info("extension %r unloaded successfully", path)

    async def reload_extensions(self, *import_paths: str) -> None:
        """
        Reload extensions from the given import paths. This operation is **atomic**. If reloading of an extension
        fails, the client's state for that extension will be restored to the previous known-working state. If
        a path is passed for an extension that is **not** loaded, it will be loaded and continue processing
        the remaining extensions.

        Args:
            *import_paths: The import paths for the extensions to be reloaded.

        Returns:
            :obj:`None`
        """
        for path in import_paths:
            if path not in self._extensions:
                LOGGER.debug("extension %r is not loaded - loading", path)
                await self.load_extensions(path)
                continue

            prev_extension = sys.modules[path]
            try:
                await self.unload_extensions(path)
            except Exception as e:
                LOGGER.error("error unloading extension %r - reverting", path, exc_info=(type(e), e, e.__traceback__))
                # Make load use the cached extension that we know works. We need to remove the extension
                # from the extensions set so that load doesn't just skip it
                self._extensions.remove(path)
                sys.modules[path] = prev_extension
                await self.load_extensions(path)
                continue

            # Try to load, method doesn't raise an error if the extension couldn't be loaded,
            # so we need to check if the extension was added to the client's list of extensions.
            # If it wasn't - it means the extension load was unsuccessful.
            await self.load_extensions(path)
            if path not in self._extensions:
                LOGGER.error("error loading extension %r - reverting", path)
                # Revert to previous state
                sys.modules[path] = prev_extension
                # This time the method is called, it will use the cached version of the extension
                # that worked previously - load_extensions will have cleaned itself up if the previous load failed.
                await self.load_extensions(path)
                continue

            LOGGER.info("extension %r reloaded successfully", path)

    async def _ensure_application(self) -> hikari.PartialApplication:
        if self._application is not None:
            return self._application

        self._application = await self.rest.fetch_application()
        return self._application

    async def sync_application_commands(self) -> None:
        """
        Sync all application commands registered to the bot with discord. Also, properly registers any commands
        with localization enabled for the command name as well as any commands using deferred registration.

        Returns:
            :obj:`None`
        """
        if self._localized_commands and self.localization_provider is localization.localization_unsupported:
            raise RuntimeError("some commands are marked as localized but no localization provider is available")

        for guilds, command in self._localized_commands:
            builder = await command.as_command_builder(self.default_locale, self.localization_provider)

            for guild in guilds:
                self._commands[guild][builder.name].put(command)

        if self._deferred_commands and self.deferred_registration_callback is None:
            raise RuntimeError("some commands have deferred registration but no callback is available")

        for command in self._deferred_commands:
            builder = await command.as_command_builder(self.default_locale, self.localization_provider)

            assert self.deferred_registration_callback is not None
            guilds = await utils.maybe_await(self.deferred_registration_callback(command))

            for guild in [guilds] if isinstance(guilds, int) else guilds:
                self._commands[guild][builder.name].put(command)

        await sync.sync_application_commands(self)

    @staticmethod
    def _get_subcommand(
        options: t.Sequence[OptionT],
    ) -> OptionT | None:
        subcommand = filter(
            lambda o: o.type in (hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP), options
        )
        return next(subcommand, None)

    @t.overload
    def _resolve_options_and_command(
        self, interaction: hikari.AutocompleteInteraction
    ) -> tuple[t.Sequence[hikari.AutocompleteInteractionOption], type[commands.CommandBase]] | None: ...

    @t.overload
    def _resolve_options_and_command(
        self, interaction: hikari.CommandInteraction
    ) -> tuple[t.Sequence[hikari.CommandInteractionOption], type[commands.CommandBase]] | None: ...

    def _resolve_options_and_command(
        self, interaction: hikari.AutocompleteInteraction | hikari.CommandInteraction
    ) -> (
        tuple[
            t.Sequence[hikari.AutocompleteInteractionOption] | t.Sequence[hikari.CommandInteractionOption],
            type[commands.CommandBase],
        ]
        | None
    ):
        command_path = [interaction.command_name]

        subcommand: hikari.CommandInteractionOption | hikari.AutocompleteInteractionOption | None
        options = interaction.options or []
        while (subcommand := self._get_subcommand(options)) is not None:
            command_path.append(subcommand.name)
            options = subcommand.options or []

        global_commands = self._commands.get(constants.GLOBAL_COMMAND_KEY, {}).get(interaction.command_name)
        guild_commands = self._commands.get(interaction.registered_guild_id or constants.GLOBAL_COMMAND_KEY, {}).get(
            interaction.command_name
        )

        root_commands = guild_commands if interaction.registered_guild_id is not None else global_commands
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

        return options, command

    def build_autocomplete_context(
        self,
        interaction: hikari.AutocompleteInteraction,
        options: t.Sequence[hikari.AutocompleteInteractionOption],
        command_cls: type[commands.CommandBase],
    ) -> context_.AutocompleteContext[t.Any]:
        """
        Build a context object from the given parameters.

        Args:
            interaction: The interaction for the autocomplete invocation.
            options: The options supplied with the interaction.
            command_cls: The command class that represents the command that has the option being autocompleted.

        Returns:
            :obj:`~lightbulb.context.AutocompleteContext`: The built context.
        """
        return context_.AutocompleteContext(self, interaction, options, command_cls)

    async def _execute_autocomplete_context(
        self, context: context_.AutocompleteContext[t.Any], autocomplete_provider: options_.AutocompleteProvider[t.Any]
    ) -> None:
        async with self.di.enter_context(di_.Contexts.AUTOCOMPLETE) as container:
            if container is not None:  # type: ignore[reportUnnecessaryComparison]
                container.add_value(context_.AutocompleteContext, context)

            try:
                await autocomplete_provider(context)
            except Exception as e:
                LOGGER.error(
                    "error encountered during invocation of autocomplete for command %r",
                    context.command._command_data.qualified_name,
                    exc_info=(type(e), e, e.__traceback__),
                )

    async def handle_autocomplete_interaction(self, interaction: hikari.AutocompleteInteraction) -> None:
        if not self._started:
            LOGGER.debug("ignoring autocomplete interaction received before the client was started")
            return

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
        command_cls: type[commands.CommandBase],
    ) -> context_.Context:
        """
        Build a context object from the given parameters.

        Args:
            interaction: The interaction for the command invocation.
            options: The options to use to invoke the command with.
            command_cls: The command class that represents the command that should be invoked for the interaction.

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
        pipeline = execution.ExecutionPipeline(context, self.execution_step_order)

        async with self.di.enter_context(di_.Contexts.COMMAND) as container:
            if container is not None:  # type: ignore[reportUnnecessaryComparison]
                container.add_value(context_.Context, context)
                container.add_value(execution.ExecutionPipeline, pipeline)

            try:
                await pipeline._run()
            except exceptions.ExecutionPipelineFailedException as ex:
                all_handlers = [handler for handlers in self._error_handlers.values() for handler in handlers]

                handled = False
                while all_handlers and not handled:
                    handled = await (all_handlers.pop(0))(ex)

                if not handled:
                    LOGGER.error(
                        "error encountered during invocation of command %r",
                        context.command._command_data.qualified_name,
                        exc_info=(type(ex), ex, ex.__traceback__),
                    )

    async def handle_application_command_interaction(self, interaction: hikari.CommandInteraction) -> None:
        if not self._started:
            LOGGER.debug("ignoring command interaction received before the client was started")
            return

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

    Warning:
        This client **will not** be started automatically (see: :meth:`~Client.start`). It is recommended
        that you start the client in a listener for :obj:`~hikari.StartedEvent`. You should ensure that any
        commands are registered and extensions have been loaded **before** starting the client - otherwise
        command syncing may not work properly.

        For example:

        .. code-block:: python

            bot = hikari.GatewayBot(...)
            client = lightbulb.client_from_app(bot, ...)

            bot.subscribe(hikari.StartedEvent, client.start)
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

        if isinstance(app, hikari.GatewayBot):
            self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.GatewayBot, app)
        self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.api.EventManager, app.event_manager)

    @property
    def app(self) -> GatewayClientAppT:
        return self._app


class RestEnabledClient(Client):
    """
    Client implementation for applications that support an interaction server.

    Warning:
        This client should not be instantiated manually. Use :func:`~client_from_app` instead.

    Warning:
        This client **will not** be started automatically (see: :meth:`~Client.start`). It is recommended
        that you start the client in a :obj:`~hikari.impl.rest_bot.RESTBot` startup callback. You should ensure that any
        commands are registered and extensions have been loaded **before** starting the client - otherwise
        command syncing may not work properly.

        For example:

        .. code-block:: python

            bot = hikari.RESTBot(...)
            client = lightbulb.client_from_app(bot, ...)

            bot.add_startup_callback(client.start)
    """

    __slots__ = ("_app",)

    def __init__(self, app: RestClientAppT, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(app.rest, *args, **kwargs)
        self._app = app

        app.interaction_server.set_listener(hikari.AutocompleteInteraction, self.handle_rest_autocomplete_interaction)
        app.interaction_server.set_listener(hikari.CommandInteraction, self.handle_rest_application_command_interaction)

        if isinstance(app, hikari.RESTBot):
            self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.RESTBot, app)
        self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.api.InteractionServer, app.interaction_server)

    @property
    def app(self) -> RestClientAppT:
        return self._app

    def build_rest_autocomplete_context(
        self,
        interaction: hikari.AutocompleteInteraction,
        options: t.Sequence[hikari.AutocompleteInteractionOption],
        command_cls: type[commands.CommandBase],
        response_callback: t.Callable[[hikari.api.InteractionResponseBuilder], None],
    ) -> context_.AutocompleteContext[t.Any]:
        return context_.RestAutocompleteContext(self, interaction, options, command_cls, response_callback)

    async def handle_rest_autocomplete_interaction(
        self, interaction: hikari.AutocompleteInteraction
    ) -> t.AsyncGenerator[hikari.api.InteractionAutocompleteBuilder, t.Any]:
        if not self._started:
            LOGGER.debug("ignoring autocomplete interaction received before the client was started")
            return

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
        command_cls: type[commands.CommandBase],
        response_callback: t.Callable[[hikari.api.InteractionResponseBuilder], None],
    ) -> context_.Context:
        return context_.RestContext(self, interaction, options, command_cls(), response_callback)

    async def handle_rest_application_command_interaction(
        self, interaction: hikari.CommandInteraction
    ) -> t.AsyncGenerator[
        hikari.api.InteractionDeferredBuilder
        | hikari.api.InteractionMessageBuilder
        | hikari.api.InteractionModalBuilder,
        t.Any,
    ]:
        if not self._started:
            LOGGER.debug("ignoring command interaction received before the client was started")
            return

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


@t.overload
def client_from_app(
    app: GatewayClientAppT,
    default_enabled_guilds: t.Sequence[hikari.Snowflakeish] = (constants.GLOBAL_COMMAND_KEY,),
    execution_step_order: t.Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
    default_locale: hikari.Locale = hikari.Locale.EN_US,
    localization_provider: localization.LocalizationProviderT = localization.localization_unsupported,
    delete_unknown_commands: bool = True,
    deferred_registration_callback: t.Callable[
        [CommandOrGroup], MaybeAwaitable[hikari.Snowflakeish | t.Sequence[hikari.Snowflakeish]]
    ]
    | None = None,
) -> GatewayEnabledClient: ...
@t.overload
def client_from_app(
    app: RestClientAppT,
    default_enabled_guilds: t.Sequence[hikari.Snowflakeish] = (constants.GLOBAL_COMMAND_KEY,),
    execution_step_order: t.Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
    default_locale: hikari.Locale = hikari.Locale.EN_US,
    localization_provider: localization.LocalizationProviderT = localization.localization_unsupported,
    delete_unknown_commands: bool = True,
    deferred_registration_callback: t.Callable[
        [CommandOrGroup], MaybeAwaitable[hikari.Snowflakeish | t.Sequence[hikari.Snowflakeish]]
    ]
    | None = None,
) -> RestEnabledClient: ...
def client_from_app(
    app: GatewayClientAppT | RestClientAppT,
    default_enabled_guilds: t.Sequence[hikari.Snowflakeish] = (constants.GLOBAL_COMMAND_KEY,),
    execution_step_order: t.Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
    default_locale: hikari.Locale = hikari.Locale.EN_US,
    localization_provider: localization.LocalizationProviderT = localization.localization_unsupported,
    delete_unknown_commands: bool = True,
    deferred_registration_callback: t.Callable[
        [CommandOrGroup], MaybeAwaitable[hikari.Snowflakeish | t.Sequence[hikari.Snowflakeish]]
    ]
    | None = None,
) -> Client:
    """
    Create and return the appropriate client implementation from the given application.

    Args:
        app: Application that either supports gateway events, or an interaction server.
        default_enabled_guilds: The guilds that application commands should be created in by default.
        execution_step_order: The order that execution steps will be run in upon command processing.
        default_locale: The default locale to use for command names and descriptions,
            as well as option names and descriptions. Has no effect if localizations are not being used.
            Defaults to :obj:`hikari.locales.Locale.EN_US`.
        localization_provider: The localization provider function to use. This will be called whenever the
            client needs to get the localizations for a key. Defaults to
            :obj:`~lightbulb.localization.localization_unsupported` - the client does not support localizing commands.
            **Must** be passed if you intend to support localizations.
        delete_unknown_commands: Whether to delete existing commands that the client does not have
            an implementation for during command syncing. Defaults to :obj:`True`.
        deferred_registration_callback: The callback to use to resolve which guilds a command should be created in
            if a command is registered using :meth:`~Client.register_deferred`. Allows for commands to be
            dynamically created in guilds, for example enabled on a per-guild basis using feature flags. Defaults
            to :obj:`None`.

    Returns:
        :obj:`~Client`: The created client instance.
    """
    if execution.ExecutionSteps.INVOKE not in execution_step_order:
        raise ValueError("'execution_step_order' must include ExecutionSteps.INVOKE")

    if isinstance(app, GatewayClientAppT):
        LOGGER.debug("building gateway client from app")
        cls = GatewayEnabledClient
    else:
        LOGGER.debug("building REST client from app")
        cls = RestEnabledClient

    return cls(
        app,  # type: ignore[reportArgumentType]
        default_enabled_guilds,
        execution_step_order,
        default_locale,
        localization_provider,
        delete_unknown_commands,
        deferred_registration_callback,
    )
