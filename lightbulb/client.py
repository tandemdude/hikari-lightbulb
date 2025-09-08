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
import importlib
import logging
import pathlib
import sys
import typing as t

import async_timeout
import hikari
import linkd

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
from lightbulb.internal import types as lb_types
from lightbulb.internal import utils as i_utils

if t.TYPE_CHECKING:
    import types
    from collections.abc import AsyncGenerator
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Coroutine
    from collections.abc import Mapping
    from collections.abc import Sequence

    from lightbulb import features as features_
    from lightbulb.commands import options as options_
    from lightbulb.components import menus

T = t.TypeVar("T")
CommandOrGroupT = t.TypeVar("CommandOrGroupT", bound=lb_types.CommandOrGroup)
ErrorHandlerT = t.TypeVar("ErrorHandlerT", bound=lb_types.ErrorHandler)
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
        hooks: Execution hooks that should be applied to all commands. These hooks will always run **before**
            all other hooks registered for the same step are executed.
    """

    __slots__ = (
        "_application",
        "_asyncio_tasks",
        "_attached_menus",
        "_attached_modals",
        "_command_invocation_mapping",
        "_created_commands",
        "_current_extension_being_loaded",
        "_di",
        "_error_handlers",
        "_extensions",
        "_features",
        "_localization",
        "_menu_queues",
        "_owner_ids",
        "_registered_commands",
        "_started",
        "_tasks",
        "default_enabled_guilds",
        "default_locale",
        "deferred_registration_callback",
        "delete_unknown_commands",
        "execution_step_order",
        "hooks",
        "localization_provider",
        "rest",
        "sync_commands",
    )

    def __init__(
        self,
        rest: hikari.api.RESTClient,
        default_enabled_guilds: Sequence[hikari.Snowflakeish],
        execution_step_order: Sequence[execution.ExecutionStep],
        default_locale: hikari.Locale,
        localization_provider: localization.LocalizationProvider,
        delete_unknown_commands: bool,
        deferred_registration_callback: lb_types.DeferredRegistrationCallback | None,
        hooks: Sequence[execution.ExecutionHook],
        sync_commands: bool,
        *,
        features: Sequence[features_.Feature],
    ) -> None:
        super().__init__()

        self.rest: hikari.api.RESTClient = rest
        self.default_enabled_guilds: Sequence[hikari.Snowflakeish] = default_enabled_guilds
        self.execution_step_order: Sequence[execution.ExecutionStep] = execution_step_order
        self.default_locale: hikari.Locale = default_locale
        self.localization_provider: localization.LocalizationProvider = localization_provider
        self.delete_unknown_commands: bool = delete_unknown_commands
        self.deferred_registration_callback: lb_types.DeferredRegistrationCallback | None = (
            deferred_registration_callback
        )
        self.hooks: Sequence[execution.ExecutionHook] = hooks
        self.sync_commands: bool = sync_commands

        self._features = set(features)
        self._di = linkd.DependencyInjectionManager()

        self._registered_commands: dict[
            lb_types.CommandOrGroup, Collection[hikari.Snowflakeish] | t.Literal["defer"]
        ] = {}
        self._command_invocation_mapping: dict[
            hikari.Snowflakeish, dict[tuple[str, ...], i_utils.CommandCollection]
        ] = collections.defaultdict(lambda: collections.defaultdict(i_utils.CommandCollection))
        self._created_commands: dict[hikari.Snowflakeish, Collection[hikari.PartialCommand]] = {}

        self._error_handlers: dict[int, list[lb_types.ErrorHandler]] = {}
        self._application: hikari.Application | None = None

        self._extensions: set[str] = set()
        self._current_extension_being_loaded: str | None = None

        self._tasks: set[tasks.Task] = set()

        self._attached_menus: set[menus._MenuInteractionHandlerContainer] = set()
        self._attached_modals: dict[str, Callable[[hikari.ModalInteraction, asyncio.Event], t.Awaitable[None]]] = {}

        self._asyncio_tasks: set[asyncio.Task[t.Any]] = set()

        self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.api.RESTClient, self.rest)
        self.di.registry_for(di_.Contexts.DEFAULT).register_value(Client, self)

        self._started = False

        self._owner_ids: set[hikari.Snowflakeish] | None = None

    def _handle_task_done(self, task: asyncio.Task[t.Any]) -> None:
        self._asyncio_tasks.discard(task)

        if task.cancelled():
            return

        if (exc := task.exception()) is not None:
            if isinstance(exc, asyncio.TimeoutError) and task.get_name().endswith("@notimeout"):
                return

            asyncio.get_running_loop().call_exception_handler(
                {
                    "message": "an exception occurred during task execution",
                    "exception": exc,
                    "task": task,
                }
            )

    @property
    @abc.abstractmethod
    def app(self) -> hikari.RESTAware:
        """The app that this client was created from."""

    @property
    def di(self) -> linkd.DependencyInjectionManager:
        """The dependency injection manager used by this client."""
        return self._di

    @property
    def registered_commands(self) -> Sequence[lb_types.CommandOrGroup]:
        """
        Sequence of the command classes and group instances registered to this client. This will not
        contain any subcommands or subgroups.

        Note:
            This **may** contain commands that have not yet been synced with discord.
        """
        return [c for c in self._registered_commands]

    @property
    def invokable_commands(self) -> Mapping[hikari.Snowflakeish, Mapping[tuple[str, ...], i_utils.CommandCollection]]:
        """
        Mapping of guild ID to mapping of qualified command path to command(s) (slash, message, and user) that can
        be invoked for that command path.

        Example:

            If the following global commands are registered:

            .. code-block::

                /command
                /group
                ├── subcommand
                └── subgroup
                    └── subsubcommand

            This would return the following mapping:

            .. code-block:: python

                {0: {
                    ("command",): CommandCollection(slash=Command, message=None, user=None),
                    ("group", "subcommand"): CommandCollection(slash=Subcommand, message=None, user=None),
                    ("group", "subgroup", "subsubcommand"): CommandCollection(slash=Subsubcommand, message=None, user=None),
                }}

        Note:
            This **may** contain commands that have not yet been synced with discord.
        """  # noqa: E501
        return self._command_invocation_mapping

    @property
    def created_commands(self) -> Mapping[hikari.Snowflakeish, Collection[hikari.PartialCommand]]:
        """
        Mapping of guild ID to commands that were created in that guild during command syncing.

        Global commands are stored at the key :data:`lightbulb.internal.constants.GLOBAL_COMMAND_KEY`.
        """
        return self._created_commands

    def safe_create_task(self, coro: Coroutine[None, None, T]) -> asyncio.Task[T]:
        """
        Safely create an asyncio task.

        Asyncio tasks to be stored in some variable or collection to avoid cancellation
        due a GC cycle. This function handles storing the task until completion, as well as
        registering a done callback to report any errors the task may have raised to the asyncio
        exception handler.

        Args:
            coro: The coroutine to run in the task.

        Returns:
            The created task.

        .. versionadded:: 3.0.2
        """
        task = asyncio.create_task(coro)
        self._asyncio_tasks.add(task)
        task.add_done_callback(self._handle_task_done)
        return task

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
    ) -> Callable[[tasks.TaskFunc], tasks.Task]: ...
    @t.overload
    def task(self, task: tasks.Task, /) -> tasks.Task: ...

    def task(  # noqa: D417
        self,
        task_or_trigger: tasks.Trigger | tasks.Task,
        /,
        auto_start: bool = True,
        max_failures: int = 1,
        max_invocations: int = -1,
    ) -> Callable[[tasks.TaskFunc], tasks.Task] | tasks.Task:
        """
        Second order decorator to register a repeating task with the client. Task functions will have
        dependency injection enabled on them automatically. Task functions **must** be asynchronous.

        Args:
            task: The task to register with the client. If this parameter is provided then all other parameters
                are ignored.
            trigger: The trigger function to use to resolve the interval between task executions.
            auto_start: Whether the task should be started automatically. This means that if the task is added to
                the client upon the client being started, the task will also be started; it will also be started
                if added to an already-started client.
            max_failures: The maximum number of failed attempts to execute the task before it is cancelled.
                Setting this to a negative number will prevent the task from being cancelled, regardless of
                how often the task fails.
            max_invocations: The maximum number of times the task can be invoked before being stopped.
                Setting this to a negative number will disable this behaviour, allowing unlimited invocations.

        Note:
            This method can also be called with an existing task object to register it directly.

        Example:

            .. code-block:: python

                @client.task(lightbulb.uniformtrigger(minutes=1))
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
    def error_handler(self, *, priority: int = 0) -> Callable[[ErrorHandlerT], ErrorHandlerT]: ...

    @t.overload
    def error_handler(self, func: ErrorHandlerT, *, priority: int = 0) -> ErrorHandlerT: ...

    def error_handler(
        self, func: ErrorHandlerT | None = None, *, priority: int = 0
    ) -> ErrorHandlerT | Callable[[ErrorHandlerT], ErrorHandlerT]:
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
            handlers_with_same_priority.append(wrapped)  # type: ignore[reportArgumentType]
            self._error_handlers[priority] = handlers_with_same_priority

            sorted_handlers = sorted(self._error_handlers.items(), key=lambda item: item[0], reverse=True)
            self._error_handlers = {k: v for k, v in sorted_handlers}

            return t.cast("ErrorHandlerT", wrapped)

        def _inner(func_: ErrorHandlerT) -> ErrorHandlerT:
            return self.error_handler(func_, priority=priority)

        return _inner

    def remove_error_handler(self, func: lb_types.ErrorHandler) -> None:
        """
        Unregister a command error handler function from the client.

        Args:
            func: The function to unregister as a command error handler.

        Returns:
            :obj:`None`
        """
        new_handlers: dict[int, list[lb_types.ErrorHandler]] = {}
        for priority, handlers in self._error_handlers.items():
            handlers = [
                h for h in handlers if h is not func and (isinstance(h, linkd.AutoInjecting) and h._func is not func)
            ]
            if handlers:
                new_handlers[priority] = t.cast("list[lb_types.ErrorHandler]", handlers)

        sorted_handlers = sorted(new_handlers.items(), key=lambda item: item[0], reverse=True)
        self._error_handlers = {k: v for k, v in sorted_handlers}

    @t.overload
    def register(
        self, *, guilds: Sequence[hikari.Snowflakeish] | None = None, global_: bool | None = None
    ) -> Callable[[CommandOrGroupT], CommandOrGroupT]: ...

    @t.overload
    def register(self, *, defer_guilds: t.Literal[True]) -> Callable[[CommandOrGroupT], CommandOrGroupT]: ...

    @t.overload
    def register(
        self,
        command: CommandOrGroupT,
        *,
        guilds: Sequence[hikari.Snowflakeish] | None = None,
        global_: bool | None = None,
    ) -> CommandOrGroupT: ...

    @t.overload
    def register(self, command: CommandOrGroupT, *, defer_guilds: t.Literal[True]) -> CommandOrGroupT: ...

    def register(
        self,
        command: CommandOrGroupT | None = None,
        *,
        guilds: Sequence[hikari.Snowflakeish] | None = None,
        global_: bool | None = None,
        defer_guilds: bool = False,
    ) -> CommandOrGroupT | Callable[[CommandOrGroupT], CommandOrGroupT]:
        """
        Register a command or group with this client instance.

        Optionally, a sequence of guild ids, and/or a boolean indicating whether the command should be registered
        globally can be provided to make the commands created in specific guilds  only - overriding the value
        for default enabled guilds. If you specify ``global_=False`` then you **must** specify either
        ``guilds=[...]`` in this function, or ``default_enabled_guilds`` when creating the client.

        If a value is passed to ``guilds`` or you pass ``global_=True``, then this command will not use the value
        you provided to ``default_enabled_guilds``.

        You may specify ``defer_guilds=True`` in order to resolve the guilds the command should be created in
        once the client has been started.

        This method can be used as a function, or a first or second order decorator.

        Args:
            command: The command class or command group to register with the client.
            guilds: The guilds to create the command or group in.
            global_: Whether the command should be registered globally.
            defer_guilds: Whether the guilds to create this command in should be resolved when the client is started.
                If :obj:`True`, the ``deferred_registration_callback`` will be used to resolve which guilds
                to create the command in. You can also use this to conditionally prevent the command from being
                registered to any guilds.

        Returns:
            The registered command or group, unchanged.

        Raises:
            :obj:`ValueError`: If ``defer_guilds`` is :obj:`True`, and no ``deferred_registration_callback`` was
                set upon client creation.

        Note:
            The signature overloads do not allow for you to pass a value for both ``guilds`` and ``defer_guilds``. If
            for some reason you pass both however, then ``defer_guilds`` will take precedence.

        Example:

            .. code-block:: python

                client = lightbulb.client_from_app(...)

                # valid
                @client.register
                # also valid
                @client.register(guilds=[...], global_=True)
                # also valid
                @client.register(defer_guilds=True)
                class Example(
                    lightbulb.SlashCommand,
                    ...
                ):
                    ...

                # also valid
                client.register(Example, guilds=[...], global_=True)
                # also valid
                client.register(Example, defer_guilds=True)

            .. code-block:: python

                client = lightbulb.client_from_app(..., default_enabled_guilds=[123, 456])

                # Command will be registered in:
                # guilds: 123, 456
                # globally: false
                client.register(command)

                # guilds: 123, 456
                # globally: false
                client.register(command, global_=False)

                # guilds: 789
                # globally: false
                client.register(command, guilds=[789])

                # guilds: none
                # globally: true
                client.register(command, global_=True)

                # guilds: 789
                # globally: true
                client.register(command, guilds=[789], global_=True)

                # === IF NO 'default_enabled_guilds' SET ===

                # guilds: none
                # globally: true
                client.register(command)
        """
        register_in: set[hikari.Snowflakeish] = set()

        if guilds is None and global_ is None:
            register_in.update(self.default_enabled_guilds or (constants.GLOBAL_COMMAND_KEY,))
        elif global_ is False:
            if not guilds and not self.default_enabled_guilds:
                raise ValueError("cannot set 'global_=False' without specifying 'guilds' or 'default_enabled_guilds'")
            register_in.update(guilds or self.default_enabled_guilds)
        else:
            register_in.update(guilds or ())
            if global_:
                register_in.add(constants.GLOBAL_COMMAND_KEY)

        # Used as a function or first-order decorator
        if command is not None:
            self._registered_commands[command] = "defer" if defer_guilds else register_in
            LOGGER.debug("command %r registered successfully", command)
            return command

        # Used as a second-order decorator
        def _inner(command_: CommandOrGroupT) -> CommandOrGroupT:
            if defer_guilds:
                return self.register(command_, defer_guilds=True)
            return self.register(command_, guilds=guilds, global_=global_)

        return _inner

    def unregister(self, command: lb_types.CommandOrGroup) -> None:
        """
        Unregister a command with the client. This will prevent the client from handling any incoming
        interactions for the given command globally, or in any guild. This **will not** delete the command from
        discord and users will still be able to see it in the command menu.

        Args:
            command: The command class or command group to unregister with the client.

        Returns:
            :obj:`None`
        """
        # If this is a group, we need to manually remove all subcommands from the command invocation mapping
        # since the collection.remove() only handles the top-level group
        if isinstance(command, groups.Group):
            for guild_id, mapping in self._command_invocation_mapping.items():
                self._command_invocation_mapping[guild_id] = {
                    path: collection
                    for path, collection in mapping.items()
                    if not (len(path) > 1 and path[0] == command.name)
                }
        else:
            # For regular commands, just remove them from collections
            for mapping in self._command_invocation_mapping.values():
                for collection in mapping.values():
                    collection.remove(command)

        self._registered_commands.pop(command, None)

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
                self._current_extension_being_loaded = path
            except ImportError as e:
                LOGGER.error("error importing extension %r - skipping", path, exc_info=(type(e), e, e.__traceback__))
                continue

            loaded: list[loaders.Loader] = []
            any_skipped: bool = False

            maybe_loader: loaders.Loader | None = None
            try:
                for name in dir(extension):
                    if not isinstance(item := getattr(extension, name, None), loaders.Loader) or item in loaded:
                        continue

                    maybe_loader = item

                    if not await utils.maybe_await(maybe_loader._should_load_hook()):
                        any_skipped = True
                        continue

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

                self._current_extension_being_loaded = None
                continue

            self._current_extension_being_loaded = None

            if not loaded and not any_skipped:
                LOGGER.warning("found no loaders in extension %r - skipping", path)
                continue

            self._extensions.add(path)
            LOGGER.info("extension %r loaded successfully", path)

        # ensure that any commands are made available for the interaction handler
        if self._started:
            await self.sync_application_commands(_force_no_api_call=True)

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

    async def _ensure_application(self) -> hikari.Application:
        if self._application is not None:
            return self._application

        self._application = await self.rest.fetch_application()
        return self._application

    async def sync_application_commands(self, *, _force_no_api_call: bool = False) -> None:
        """
        Sync all application commands registered to the bot with discord. Also, properly registers any commands
        with localization enabled for the command name as well as any commands using deferred registration.

        Returns:
            :obj:`None`
        """
        for command, data in self._registered_commands.items():
            if data == "defer":
                if self.deferred_registration_callback is None:
                    raise RuntimeError(
                        "one or more commands marked as deferred but no 'deferred_registration_callback' was provided"
                    )
                deferred_registration_data = await utils.maybe_await(self.deferred_registration_callback(command))
                if deferred_registration_data is None:
                    continue

                register_in, globally = set(deferred_registration_data[0]), deferred_registration_data[1]
                if globally:
                    register_in.add(constants.GLOBAL_COMMAND_KEY)
            else:
                register_in = data

            builder = await command.as_command_builder(self.default_locale, self.localization_provider)
            if isinstance(command, groups.Group):
                all_commands: dict[tuple[str, ...], type[commands.CommandBase]] = {}

                for subcommand_or_subgroup in command.subcommands.values():
                    subcommand_or_subgroup_option = await subcommand_or_subgroup.to_command_option(
                        self.default_locale, self.localization_provider
                    )

                    if isinstance(subcommand_or_subgroup, groups.SubGroup):
                        for subcommand in subcommand_or_subgroup.subcommands.values():
                            subcommand_option = await subcommand.to_command_option(
                                self.default_locale, self.localization_provider
                            )
                            all_commands[(builder.name, subcommand_or_subgroup_option.name, subcommand_option.name)] = (  # noqa: RUF031
                                subcommand
                            )
                    else:
                        all_commands[(builder.name, subcommand_or_subgroup_option.name)] = subcommand_or_subgroup  # noqa: RUF031
            else:
                all_commands = {(builder.name,): command}

            for snowflake in register_in:
                for command_path, actual_command in all_commands.items():
                    self._command_invocation_mapping[snowflake][command_path].put(actual_command)

        if _force_no_api_call:
            return

        if self.sync_commands:
            await sync.sync_application_commands(self)

    @staticmethod
    def _get_subcommand(
        options: Sequence[OptionT],
    ) -> OptionT | None:
        subcommand = filter(
            lambda o: o.type in (hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP), options
        )
        return next(subcommand, None)

    @t.overload
    def _resolve_options_and_command(
        self, interaction: hikari.AutocompleteInteraction
    ) -> tuple[Sequence[hikari.AutocompleteInteractionOption], type[commands.CommandBase]] | None: ...

    @t.overload
    def _resolve_options_and_command(
        self, interaction: hikari.CommandInteraction
    ) -> tuple[Sequence[hikari.CommandInteractionOption], type[commands.CommandBase]] | None: ...

    def _resolve_options_and_command(
        self, interaction: hikari.AutocompleteInteraction | hikari.CommandInteraction
    ) -> (
        tuple[
            Sequence[hikari.AutocompleteInteractionOption] | Sequence[hikari.CommandInteractionOption],
            type[commands.CommandBase],
        ]
        | None
    ):
        command_path = [interaction.command_name]

        subcommand: hikari.CommandInteractionOption | hikari.AutocompleteInteractionOption | None
        options: Sequence[hikari.CommandInteractionOption] = interaction.options or []
        while (subcommand := self._get_subcommand(options)) is not None:
            command_path.append(subcommand.name)
            options = subcommand.options or []

        global_commands = self._command_invocation_mapping.get(constants.GLOBAL_COMMAND_KEY, {}).get(
            tuple(command_path)
        )
        guild_commands = self._command_invocation_mapping.get(
            interaction.registered_guild_id or constants.GLOBAL_COMMAND_KEY, {}
        ).get(tuple(command_path))

        root_commands = guild_commands if interaction.registered_guild_id is not None else global_commands
        if root_commands is None:
            LOGGER.debug("ignoring interaction received for unknown command - %r", interaction.command_name)
            return None

        command = {
            int(hikari.CommandType.SLASH): root_commands.slash,
            int(hikari.CommandType.USER): root_commands.user,
            int(hikari.CommandType.MESSAGE): root_commands.message,
        }[int(interaction.command_type)]

        if command is None:
            LOGGER.debug("ignoring interaction received for unknown command - %r", " ".join(command_path))
            return None

        return options, command

    def build_autocomplete_context(
        self,
        interaction: hikari.AutocompleteInteraction,
        options: Sequence[hikari.AutocompleteInteractionOption],
        command_cls: type[commands.CommandBase],
        initial_response_sent: asyncio.Event,
    ) -> context_.AutocompleteContext[t.Any]:
        """
        Build a context object from the given parameters.

        Args:
            interaction: The interaction for the autocomplete invocation.
            options: The options supplied with the interaction.
            command_cls: The command class that represents the command that has the option being autocompleted.
            initial_response_sent: Asyncio event that the context will set when the autocomplete response is sent.

        Returns:
            :obj:`~lightbulb.context.AutocompleteContext`: The built context.
        """
        return context_.AutocompleteContext(
            client=self,
            interaction=interaction,
            options=options,
            command=command_cls,
            initial_response_sent=initial_response_sent,
        )

    async def _execute_autocomplete_context(
        self, context: context_.AutocompleteContext[t.Any], autocomplete_provider: options_.AutocompleteProvider[t.Any]
    ) -> None:
        async with (
            self.di.enter_context(di_.Contexts.DEFAULT),
            self.di.enter_context(di_.Contexts.AUTOCOMPLETE) as container,
        ):
            container.add_value(context_.AutocompleteContext, context)

            try:
                await autocomplete_provider(context)
            except Exception as e:
                LOGGER.error(
                    "error encountered during invocation of autocomplete for command %r",
                    context.command._command_data.qualified_name,
                    exc_info=(type(e), e, e.__traceback__),
                )

    async def handle_autocomplete_interaction(
        self, interaction: hikari.AutocompleteInteraction, initial_response_sent: asyncio.Event
    ) -> None:
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

        context = self.build_autocomplete_context(interaction, options, command, initial_response_sent)

        option = next(
            filter(lambda opt: opt._localized_name == context.focused.name, command._command_data.options.values()),
            None,
        )
        if option is None or not option.autocomplete:
            LOGGER.debug("interaction appears to refer to option that has autocomplete disabled - ignoring")
            return

        LOGGER.debug("%r - invoking autocomplete", command._command_data.qualified_name)

        assert option.autocomplete_provider is not hikari.UNDEFINED
        await self._execute_autocomplete_context(context, option.autocomplete_provider)

    def build_command_context(
        self,
        interaction: hikari.CommandInteraction,
        options: Sequence[hikari.CommandInteractionOption],
        command_cls: type[commands.CommandBase],
        initial_response_sent: asyncio.Event,
    ) -> context_.Context:
        """
        Build a context object from the given parameters.

        Args:
            interaction: The interaction for the command invocation.
            options: The options to use to invoke the command with.
            command_cls: The command class that represents the command that should be invoked for the interaction.
            initial_response_sent: Asyncio event that the context will set when the initial response is sent.

        Returns:
            :obj:`~lightbulb.context.Context`: The built context.
        """
        return context_.Context(
            client=self,
            interaction=interaction,
            options=options,
            command=command_cls(),
            initial_response_sent=initial_response_sent,
        )

    async def _execute_command_context(self, context: context_.Context) -> None:
        pipeline = execution.ExecutionPipeline(context, self.execution_step_order)

        async with (
            self.di.enter_context(di_.Contexts.DEFAULT),
            self.di.enter_context(di_.Contexts.COMMAND) as container,
        ):
            container.add_value(context_.Context, context)
            container.add_value(execution.ExecutionPipeline, pipeline)

            try:
                await pipeline._run()
            except exceptions.ExecutionPipelineFailedException as ex:
                all_handlers = [handler for handlers in self._error_handlers.values() for handler in handlers]

                handled = False
                while all_handlers and not handled:
                    handled = await utils.maybe_await((all_handlers.pop(0))(ex))

                if not handled:
                    LOGGER.error(
                        "error encountered during invocation of command %r",
                        context.command._command_data.qualified_name,
                        exc_info=(type(ex), ex, ex.__traceback__),
                    )

    async def handle_application_command_interaction(
        self, interaction: hikari.CommandInteraction, initial_response_sent: asyncio.Event
    ) -> None:
        if not self._started:
            LOGGER.debug("ignoring command interaction received before the client was started")
            return

        out = self._resolve_options_and_command(interaction)
        if out is None:
            return

        options, command = out
        context = self.build_command_context(interaction, options or [], command, initial_response_sent)
        LOGGER.debug("invoking command - %r", command._command_data.qualified_name)
        await self._execute_command_context(context)

    async def handle_component_interaction(
        self, interaction: hikari.ComponentInteraction, initial_response_sent: asyncio.Event
    ) -> None:
        if not self._started:
            LOGGER.debug("ignoring component interaction received before the client was started")
            return

        menu = next((m for m in self._attached_menus if interaction.custom_id in m.custom_ids), None)
        if menu is None or menu.on_interaction is None:
            return

        await menu.on_interaction(interaction, initial_response_sent)

    async def handle_modal_interaction(
        self, interaction: hikari.ModalInteraction, initial_response_sent: asyncio.Event
    ) -> None:
        if not self._started:
            LOGGER.debug("ignoring modal interaction received before the client was started")
            return

        handler = self._attached_modals.get(interaction.custom_id)
        if handler is None:
            return

        await handler(interaction, initial_response_sent)

    async def handle_interaction_create(
        self, interaction: hikari.PartialInteraction, initial_response_sent_event: asyncio.Event | None = None
    ) -> None:
        initial_response_sent_event = initial_response_sent_event or asyncio.Event()

        if isinstance(interaction, hikari.AutocompleteInteraction):
            await self.handle_autocomplete_interaction(interaction, initial_response_sent_event)
        elif isinstance(interaction, hikari.CommandInteraction):
            await self.handle_application_command_interaction(interaction, initial_response_sent_event)
        elif isinstance(interaction, hikari.ComponentInteraction):
            await self.handle_component_interaction(interaction, initial_response_sent_event)
        elif isinstance(interaction, hikari.ModalInteraction):
            await self.handle_modal_interaction(interaction, initial_response_sent_event)


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

        async def handle_interaction(event: hikari.InteractionCreateEvent) -> None:
            await self.handle_interaction_create(event.interaction)

        app.event_manager.subscribe(hikari.InteractionCreateEvent, handle_interaction)

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

        app.interaction_server.set_listener(hikari.AutocompleteInteraction, self.handle_rest_interaction)
        app.interaction_server.set_listener(hikari.CommandInteraction, self.handle_rest_interaction)
        app.interaction_server.set_listener(hikari.ComponentInteraction, self.handle_rest_interaction)
        app.interaction_server.set_listener(hikari.ModalInteraction, self.handle_rest_interaction)

        if isinstance(app, hikari.RESTBot):
            self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.RESTBot, app)
        self.di.registry_for(di_.Contexts.DEFAULT).register_value(hikari.api.InteractionServer, app.interaction_server)

    @property
    def app(self) -> RestClientAppT:
        return self._app

    async def handle_rest_interaction(self, interaction: hikari.PartialInteraction) -> AsyncGenerator[None, None]:
        task = self.safe_create_task(self.handle_interaction_create(interaction, (ir := asyncio.Event())))
        try:
            async with async_timeout.timeout(5):
                await ir.wait()
                yield None
        except asyncio.TimeoutError:
            task.cancel("timed out before creating initial response")

        await task


@t.overload
def client_from_app(
    app: GatewayClientAppT,
    default_enabled_guilds: Sequence[hikari.Snowflakeish] = (),
    execution_step_order: Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
    default_locale: hikari.Locale = hikari.Locale.EN_US,
    localization_provider: localization.LocalizationProvider = localization.localization_unsupported,
    delete_unknown_commands: bool = True,
    deferred_registration_callback: lb_types.DeferredRegistrationCallback | None = None,
    hooks: Sequence[execution.ExecutionHook] = (),
    sync_commands: bool = True,
    *,
    features: Sequence[features_.Feature] = (),
) -> GatewayEnabledClient: ...
@t.overload
def client_from_app(
    app: RestClientAppT,
    default_enabled_guilds: Sequence[hikari.Snowflakeish] = (),
    execution_step_order: Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
    default_locale: hikari.Locale = hikari.Locale.EN_US,
    localization_provider: localization.LocalizationProvider = localization.localization_unsupported,
    delete_unknown_commands: bool = True,
    deferred_registration_callback: lb_types.DeferredRegistrationCallback | None = None,
    hooks: Sequence[execution.ExecutionHook] = (),
    sync_commands: bool = True,
    *,
    features: Sequence[features_.Feature] = (),
) -> RestEnabledClient: ...
def client_from_app(
    app: GatewayClientAppT | RestClientAppT,
    default_enabled_guilds: Sequence[hikari.Snowflakeish] = (),
    execution_step_order: Sequence[execution.ExecutionStep] = DEFAULT_EXECUTION_STEP_ORDER,
    default_locale: hikari.Locale = hikari.Locale.EN_US,
    localization_provider: localization.LocalizationProvider = localization.localization_unsupported,
    delete_unknown_commands: bool = True,
    deferred_registration_callback: lb_types.DeferredRegistrationCallback | None = None,
    hooks: Sequence[execution.ExecutionHook] = (),
    sync_commands: bool = True,
    *,
    features: Sequence[features_.Feature] = (),
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
        hooks: Execution hooks that should be applied to all commands. These hooks will always run **before**
            all other hooks registered for the same step are executed.
        sync_commands: Whether to sync commands that are registered to the client before starting. Defaults
            to :obj:`True`.
        features: Experimental features to enable for this client.

    Returns:
        :obj:`~Client`: The created client instance.

    .. versionadded:: 3.2.0
        The ``features`` kwarg.
    """
    if execution.ExecutionSteps.INVOKE not in execution_step_order:
        raise ValueError("'execution_step_order' must include ExecutionSteps.INVOKE")

    if isinstance(app, GatewayClientAppT):
        LOGGER.debug("building gateway client from app")
        cls = GatewayEnabledClient
    else:
        LOGGER.debug("building REST client from app")
        cls = RestEnabledClient

    for experiment in features:
        if not di_.DI_ENABLED and experiment.requires_di_enabled:
            raise ValueError(f"cannot enable experiment {experiment.name!r} - DI is required but is disabled")

    return cls(
        app,  # type: ignore[reportArgumentType]
        default_enabled_guilds,
        execution_step_order,
        default_locale,
        localization_provider,
        delete_unknown_commands,
        deferred_registration_callback,
        hooks,
        sync_commands,
        features=features,
    )
