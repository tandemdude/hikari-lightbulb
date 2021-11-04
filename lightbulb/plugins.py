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


class Plugin:
    """
    Container class for commands and listeners that can be loaded and unloaded from the bot
    to allow for hot-swapping of commands.

    Args:
        name (:obj:`str`): The name of the plugin.
        description (Optional[:obj:`str`]): Description of the plugin. Defaults to ``None``.
        include_datastore (:obj:`bool`): Whether or not to create a :obj:`~.utils.data_store.DataStore` instance
            internally for this plugin.
    """

    __slots__ = (
        "name",
        "description",
        "d",
        "_raw_commands",
        "_all_commands",
        "_listeners",
        "_app",
        "_checks",
        "_error_handler",
        "_remove_hook",
    )

    def __init__(self, name: str, description: t.Optional[str] = None, include_datastore: bool = False) -> None:
        self.name = name
        """The plugin's name."""
        self.description = description or ""
        """The plugin's description."""
        self.d: t.Optional[data_store.DataStore] = None
        """A :obj:`~.utils.data_store.DataStore` instance enabling storage of custom data without subclassing.
        This will be ``None`` unless you explicitly specify you want the data storage instance included by passing
        in the kwarg ``include_datastore=True`` to the constructor.
        """
        if include_datastore:
            self.d = data_store.DataStore()

        self._raw_commands: t.List[commands.base.CommandLike] = []
        self._all_commands: t.List[commands.base.Command] = []

        self._listeners: t.MutableMapping[
            t.Type[hikari.Event], t.List[t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]]
        ] = defaultdict(list)

        self._checks: t.List[checks_.Check] = []
        self._error_handler: t.Optional[
            t.Callable[[events.CommandErrorEvent], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]
        ] = None
        self._remove_hook: t.Optional[t.Callable[[], t.Coroutine[t.Any, t.Any, None]]] = None

        self._app: t.Optional[app_.BotApp] = None

    @property
    def app(self) -> t.Optional[app_.BotApp]:
        """The :obj:`~.app.BotApp` instance that the plugin is registered to."""
        return self._app

    @app.setter
    def app(self, val: app_.BotApp) -> None:
        self._app = val
        # Commands need the BotApp instance in order to be instantiated
        # so we wait until the instance is injected in order to create the Command instanced
        self.create_commands()

    @property
    def bot(self) -> t.Optional[app_.BotApp]:
        """Alias for :obj:`~Plugin.app`"""
        return self._app

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
                cmd.plugin = self
                self._all_commands.append(cmd)

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
            return cmd_like

        def decorate(cmd_like_: commands.base.CommandLike) -> commands.base.CommandLike:
            self.command(cmd_like_)
            return cmd_like_

        return decorate

    def listener(
        self,
        event: t.Type[hikari.Event],
        listener_func: t.Optional[t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]] = None,
        bind: bool = False,
    ) -> t.Union[
        t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]],
        t.Callable[
            [t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]],
            t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]],
        ],
    ]:
        """
        Adds a listener function to the plugin. This method can be used as a second order decorator, or called
        manually with the event type and function to add to the plugin as a listener.

        Args:
            event (Type[:obj:`~hikari.events.base_events.Event`): Event that the listener is for.
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

        def decorate(
            func: t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]
        ) -> t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, None]]:
            # TODO - allow getting event type from type hint
            if bind:
                func = func.__get__(self)  # type: ignore
            self.listener(event, func)
            return func

        return decorate

    def error_handler(
        self,
        func: t.Optional[t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]] = None,
        bind: bool = False,
    ) -> t.Union[
        t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, t.Optional[bool]]],
        t.Callable[
            [t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]],
            t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, t.Optional[bool]]],
        ],
    ]:
        """
        Sets the error handler function for the plugin. This method can be used as a second order decorator,
        or called manually with the event type and function to set the plugin's error handler to.

        Args:
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

        def decorate(
            func_: t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]
        ) -> t.Callable[[hikari.Event], t.Coroutine[t.Any, t.Any, t.Optional[bool]]]:
            if bind:
                func_ = func_.__get__(self)  # type: ignore
            self._error_handler = func_
            return func_

        return decorate

    def remove_hook(
        self, func: t.Optional[t.Callable[[], t.Coroutine[t.Any, t.Any, None]]] = None, bind: bool = False
    ) -> t.Union[
        t.Callable[[], t.Coroutine[t.Any, t.Any, None]],
        t.Callable[[t.Callable[[], t.Coroutine[t.Any, t.Any, None]]], t.Callable[[], t.Coroutine[t.Any, t.Any, None]]],
    ]:
        """
        Sets the remove hook function for the plugin. This method can be used as a second order decorator,
        or called manually with the function to set the plugin's remove hook to. The registered function will
        be called when the plugin is removed from the bot so may be useful for teardown.

        Args:
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

        def decorate(
            func_: t.Callable[[], t.Coroutine[t.Any, t.Any, None]]
        ) -> t.Callable[[], t.Coroutine[t.Any, t.Any, None]]:
            if bind:
                func_ = func_.__get__(self)  # type: ignore
            self._remove_hook = func_
            return func_

        return decorate

    def add_checks(self, *checks: checks_.Check) -> None:
        """
        Adds one or more checks to the plugin object. These checks will be run for
        all commands in the plugin.

        Args:
            *checks (:obj:`~.checks.Check`): Check object(s) to add to the command.

        Returns:
            ``None``
        """
        self._checks.extend(checks)
