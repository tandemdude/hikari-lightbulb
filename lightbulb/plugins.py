# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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

__all__: typing.Final[typing.Tuple[str]] = [
    "EventListenerDescriptor",
    "listener",
    "Plugin",
]

import inspect
import types
import typing

import hikari

from lightbulb import commands

T = typing.TypeVar("T")
EventT_co = typing.TypeVar("EventT_co", bound=hikari.Event, covariant=True)


class EventListenerDescriptor:
    """
    Descriptor for a listener.

    This provides the same introspective logic as :meth:`hikari.Bot.listen`, but
    does so using a descriptor instead of directly subscribing the function. This
    is detected when loading plugins as a way of defining event listeners within
    plugins lazily.

    It may either consume an explicit event type, or introspect the given callback
    to get the type hint on the given callback for the event parameter after self.

    This will only work with instance-method style classes.
    """

    def __init__(
        self,
        event_type: typing.Optional[typing.Type[EventT_co]],
        callback: typing.Callable[[typing.Any, EventT_co], typing.Coroutine[typing.Any, typing.Any, None]],
    ) -> None:
        self.name: typing.Optional[str] = None
        self.callback = callback
        self.owner: typing.Optional[typing.Type[typing.Any]] = None

        signature = inspect.signature(callback)
        resolved_typehints = typing.get_type_hints(callback)
        params = []

        none_type = type(None)
        for name, param in signature.parameters.items():
            if isinstance(param.annotation, str):
                param = param.replace(
                    annotation=resolved_typehints[name] if name in resolved_typehints else inspect.Parameter.empty
                )
            if param.annotation is none_type:
                param = param.replace(annotation=None)
            params.append(param)

        return_annotation = resolved_typehints.get("return", inspect.Signature.empty)
        if return_annotation is none_type:
            return_annotation = None

        self.__signature__ = signature.replace(parameters=params, return_annotation=return_annotation)

        if event_type is None:
            if len(self.__signature__.parameters) != 2:
                raise TypeError(
                    f"Expected two positional parameters on event listener (self, event), "
                    f"got {len(self.__signature__.parameters)}"
                )

            param_iterator = iter(self.__signature__.parameters.values())
            next(param_iterator)  # discard "self"
            event_param = next(param_iterator)

            if event_param.kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY,):
                raise TypeError("Expected two positional parameters on event listener (self, event)")

            if not issubclass(event_param.annotation, hikari.Event):
                raise TypeError(
                    "Event parameter annotation type must be a subclass of hikari.Event, or an explicit "
                    "type must be given instead."
                )

            event_type = typing.cast("typing.Type[hikari.Event]", event_param.annotation)

        self.event_type = event_type

    def __set_name__(self, owner: typing.Type[typing.Any], name: str) -> None:
        self.name = name
        self.owner = owner

    @typing.no_type_check
    def __get__(self, instance: typing.Any, owner: typing.Type[typing.Any]) -> typing.Any:
        if instance is None:
            return owner
        return types.MethodType(self.callback, instance)


def listener(
    event_type: typing.Optional[typing.Type[EventT_co]] = None,
) -> typing.Callable[[T], EventListenerDescriptor]:
    """
    A decorator that registers a plugin method as an event listener.

    Args:
        event_type (Optional[ :obj:`hikari.Event` ]): The event to listen to. If
            unspecified then it will be inferred from the method's typehint.

    Example:

        .. code-block:: python

            from lightbulb import plugins
            from hikari.events.message import MessageCreateEvent

            class TestPlugin(plugins.Plugin):
                @plugins.listener(MessageCreateEvent)
                async def print_message(self, event):
                    print(event.message.content)
    """

    def decorator(listener: T) -> EventListenerDescriptor:
        return EventListenerDescriptor(event_type, listener)

    return decorator


class Plugin:
    """
    Independent class that can be loaded and unloaded from the bot
    to allow for hot-swapping of commands.

    To use in your own bot you should subclass this for each plugin
    you wish to create. Don't forget to cal ``super().__init__()`` if you
    override the ``__init__`` method.

    Args:
        name (Optional[ :obj:`str` ]): The name to register the plugin under. If unspecified will be the class name.

    Example:

        .. code-block:: python

            import lightbulb
            from lightbulb import plugins, commands

            bot = lightbulb.Bot(token="token_here", prefix="!")

            class MyPlugin(plugins.Plugin):

                @commands.command()
                async def ping(self, ctx):
                    await ctx.send("Pong!")

            bot.add_plugin(MyPlugin())
    """

    def __init__(self, *, name: str = None) -> None:
        self.name = self.__class__.__name__ if name is None else name
        """The plugin's registered name."""
        self.commands: typing.MutableMapping[str, typing.Union[commands.Command, commands.Group]] = {}
        """Mapping of command name to command object containing all commands registered to the plugin."""
        self.listeners: typing.MutableMapping[
            typing.Type[hikari.Event], typing.MutableSequence[EventListenerDescriptor],
        ] = {}
        """Mapping of event to a listener method containing all listeners registered to the plugin."""

        # we use type(self) since it will prevent the descriptor __get__ being
        # invoked to convert the command to a bound instance.
        for name, member in type(self).__dict__.items():
            if isinstance(member, commands.Command):
                if not member.is_subcommand:
                    # using self here to now get the bound command.
                    self.commands[member.name] = getattr(self, name)
                    self.commands[member.name].plugin = self

            elif isinstance(member, EventListenerDescriptor):
                if member.event_type not in self.listeners:
                    self.listeners[member.event_type] = []
                self.listeners[member.event_type].append(member)

    def __repr__(self) -> str:
        return f"<lightbulb.Plugin {self.name} at {hex(id(self))}>"
