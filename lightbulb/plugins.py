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

__all__ = ["Plugin"]

import typing as t
from collections import defaultdict

import hikari

from lightbulb.utils import data_store

if t.TYPE_CHECKING:
    from lightbulb import app as app_
    from lightbulb import checks as checks_
    from lightbulb import commands
    from lightbulb import events

ListenerT = t.TypeVar("ListenerT", bound=t.Callable[..., t.Coroutine[t.Any, t.Any, None]])
ErrorHandlerT = t.TypeVar(
    "ErrorHandlerT",
    bound=t.Callable[..., t.Coroutine[t.Any, t.Any, t.Optional[bool]]],
)
RemoveHookT = t.TypeVar("RemoveHookT", bound=t.Callable[..., t.Union[t.Coroutine[t.Any, t.Any, None], None]])


class Plugin:
    """
    Container class for commands and listeners that can be loaded and unloaded from the bot
    to allow for hot-swapping of commands.

    Args:
        name (:obj:`str`): The name of the plugin.
        description (Optional[:obj:`str`]): Description of the plugin. Defaults to ``None``.
        include_datastore (:obj:`bool`): Whether or not to create a :obj:`~.utils.data_store.DataStore` instance
            internally for this plugin.
        default_enabled_guilds (UndefinedOr[Union[:obj:`int`, Sequence[:obj:`int`]]]): The guilds to create application
            commands registered to this plugin in by default. This overrides :obj:`~.app.BotApp.default_enabled_guilds`
            but is overridden by :obj:`~.commands.base.CommandLike.guilds`.
    """

    __slots__ = (
        "name",
        "description",
        "default_enabled_guilds",
        "_d",
        "_raw_commands",
        "_all_commands",
        "_listeners",
        "_app",
        "_checks",
        "_error_handler",
        "_remove_hook",
    )

    def __init__(
        self,
        name: str,
        description: t.Optional[str] = None,
        include_datastore: bool = False,
        default_enabled_guilds: hikari.UndefinedOr[t.Union[int, t.Sequence[int]]] = hikari.UNDEFINED,
    ) -> None:
        self.name: str = name
        """The plugin's name."""
        self.description: str = description or ""
        """The plugin's description."""
        self.default_enabled_guilds: hikari.UndefinedOr[t.Sequence[int]] = (
            (default_enabled_guilds,) if isinstance(default_enabled_guilds, int) else default_enabled_guilds
        )
        """The guilds that application commands registered to this plugin will be created in by default."""

        self._d: t.Optional[data_store.DataStore] = None
        if include_datastore:
            self._d = data_store.DataStore()

        self._raw_commands: t.List[commands.base.CommandLike] = []
        self._all_commands: t.List[commands.base.Command] = []

        self._listeners: t.MutableMapping[
            t.Type[hikari.Event], t.List[t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]]
        ] = defaultdict(list)

        self._checks: t.List[t.Union[checks_.Check, checks_._ExclusiveCheck]] = []
        self._error_handler: t.Optional[
            t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]
        ] = None
        self._remove_hook: t.Optional[t.Callable[[], t.Union[t.Coroutine[t.Any, t.Any, None], None]]] = None

        self._app: t.Optional[app_.BotApp] = None

    @property
    def d(self) -> data_store.DataStore:
        """
        A :obj:`~.utils.data_store.DataStore` instance enabling storage of custom data without subclassing.
        This will raise a :obj:`RuntimeError` unless you explicitly specify you want the data
        storage instance included by passing the kwarg ``include_datastore=True`` to the constructor.
        """
        if self._d is None:
            raise RuntimeError(
                "'Plugin.d' cannot be accessed unless 'include_datastore=True' was provided during instantiation"
            )

        return self._d

    @property
    def app(self) -> app_.BotApp:
        """The :obj:`~.app.BotApp` instance that the plugin is registered to."""
        if self._app is None:
            raise RuntimeError(
                "'Plugin.app' cannot be accessed before the plugin has been added to a 'BotApp' instance"
            )

        return self._app

    @app.setter
    def app(self, val: app_.BotApp) -> None:
        self._app = val
        # Commands need the BotApp instance in order to be instantiated
        # so we wait until the instance is injected in order to create the Command instanced
        self.create_commands()

    @property
    def bot(self) -> app_.BotApp:
        """Alias for :obj:`~Plugin.app`"""
        return self.app

    @property
    def raw_commands(self) -> t.List[commands.base.CommandLike]:
        """List of all the CommandLike objects registered to the plugin."""
        return self._raw_commands

    @property
    def all_commands(self) -> t.List[commands.base.Command]:
        """List of all created command objects registered to the plugin."""
        return self._all_commands

    def create_commands(self) -> None:
        """
        Creates the command objects implemented by the :obj:`~.commands.base.CommandLike` objects registered
        to the plugin.

        Returns:
            ``None``
        """
        assert self._app is not None
        for command_like in self._raw_commands:
            commands_to_impl: t.Sequence[t.Type[commands.base.Command]] = getattr(
                command_like.callback, "__cmd_types__", []
            )
            for cmd_type in commands_to_impl:
                cmd = cmd_type(self._app, command_like)

                if cmd.is_subcommand:
                    continue

                cmd._validate_attributes()
                cmd.plugin = self
                self._all_commands.append(cmd)

    @t.overload
    def command(self, cmd_like: commands.base.CommandLike) -> commands.base.CommandLike:
        ...

    @t.overload
    def command(self) -> t.Callable[[commands.base.CommandLike], commands.base.CommandLike]:
        ...

    def command(
        self, cmd_like: t.Optional[commands.base.CommandLike] = None
    ) -> t.Union[commands.base.CommandLike, t.Callable[[commands.base.CommandLike], commands.base.CommandLike]]:
        """
        Adds a :obj:`~.commands.base.CommandLike` object as a command to the plugin. This method can be used as a
        first or second order decorator, or called manually with the :obj:`~.commands.CommandLike` instance to
        add as a command.
        """
        if cmd_like is not None:
            self._raw_commands.append(cmd_like)
            if cmd_like.guilds is hikari.UNDEFINED:
                cmd_like.guilds = self.default_enabled_guilds
            return cmd_like

        def decorate(cmd_like_: commands.base.CommandLike) -> commands.base.CommandLike:
            self.command(cmd_like_)
            return cmd_like_

        return decorate

    @t.overload
    def listener(self, event: t.Type[hikari.Event], listener_func: ListenerT, *, bind: bool = False) -> ListenerT:
        ...

    @t.overload
    def listener(self, event: t.Type[hikari.Event], *, bind: bool = False) -> t.Callable[[ListenerT], ListenerT]:
        ...

    def listener(
        self,
        event: t.Type[hikari.Event],
        listener_func: t.Optional[ListenerT] = None,
        *,
        bind: bool = False,
    ) -> t.Union[ListenerT, t.Callable[[ListenerT], ListenerT]]:
        """
        Adds a listener function to the plugin. This method can be used as a second order decorator, or called
        manually with the event type and function to add to the plugin as a listener.

        Args:
            event (Type[:obj:`~hikari.events.base_events.Event`): Event that the listener is for.

        Keyword Args:
            bind (:obj:`bool`): Whether or not to bind the listener function to the plugin. If ``True``, the
                function will be converted into a bound method and so will be called with the plugin as the
                first argument, and the error event as the second argument. Defaults to ``False``.
        """
        if listener_func is not None:
            if bind:
                listener_func = listener_func.__get__(self)  # type: ignore
            assert listener_func is not None
            self._listeners[event].append(listener_func)
            return listener_func

        def decorate(func: ListenerT) -> ListenerT:
            # TODO - allow getting event type from type hint
            if bind:
                func = func.__get__(self)  # type: ignore
            self.listener(event, func)
            return func

        return decorate

    @t.overload
    def set_error_handler(self, func: ErrorHandlerT, *, bind: bool = False) -> ErrorHandlerT:
        ...

    @t.overload
    def set_error_handler(self, *, bind: bool = False) -> t.Callable[[ErrorHandlerT], ErrorHandlerT]:
        ...

    def set_error_handler(
        self,
        func: t.Optional[ErrorHandlerT] = None,
        *,
        bind: bool = False,
    ) -> t.Union[ErrorHandlerT, t.Callable[[ErrorHandlerT], ErrorHandlerT]]:
        """
        Sets the error handler function for the plugin. This method can be used as a second order decorator,
        or called manually with the event type and function to set the plugin's error handler to.

        Keyword Args:
            bind (:obj:`bool`): Whether or not to bind the error handler function to the plugin. If ``True``, the
                function will be converted into a bound method and so will be called with the plugin as the
                first argument, and the error event as the second argument. Defaults to ``False``.
        """
        if func is not None:
            if bind:
                func = func.__get__(self)  # type: ignore
            assert func is not None
            self._error_handler = func
            return func

        def decorate(func_: ErrorHandlerT) -> ErrorHandlerT:
            if bind:
                func_ = func_.__get__(self)  # type: ignore
            self._error_handler = func_
            return func_

        return decorate

    @t.overload
    def remove_hook(self, func: RemoveHookT, *, bind: bool = False) -> RemoveHookT:
        ...

    @t.overload
    def remove_hook(self, *, bind: bool = False) -> t.Callable[[RemoveHookT], RemoveHookT]:
        ...

    def remove_hook(
        self,
        func: t.Optional[RemoveHookT] = None,
        *,
        bind: bool = False,
    ) -> t.Union[RemoveHookT, t.Callable[[RemoveHookT], RemoveHookT]]:
        """
        Sets the remove hook function for the plugin. This method can be used as a second order decorator,
        or called manually with the function to set the plugin's remove hook to. The registered function will
        be called when the plugin is removed from the bot so may be useful for teardown.

        This function will be called **after** all the members of the plugin (listeners and commands) have already
        been removed from the bot.

        Keyword Args:
            bind (:obj:`bool`): Whether or not to bind the remove hook function to the plugin. If ``True``, the
                function will be converted into a bound method and so will be called with the plugin as an
                argument. Defaults to ``False``.
        """
        if func is not None:
            if bind:
                func = func.__get__(self)  # type: ignore
            assert func is not None
            self._remove_hook = func
            return func

        def decorate(func_: RemoveHookT) -> RemoveHookT:
            if bind:
                func_ = func_.__get__(self)  # type: ignore
            self._remove_hook = func_
            return func_

        return decorate

    def add_checks(self, *checks: t.Union[checks_.Check, checks_._ExclusiveCheck]) -> None:
        """
        Adds one or more checks to the plugin object. These checks will be run for
        all commands in the plugin.

        Args:
            *checks (:obj:`~.checks.Check`): Check object(s) to add to the command.

        Returns:
            ``None``
        """
        self._checks.extend(checks)
        for check in checks:
            check.add_to_object_hook(self)
