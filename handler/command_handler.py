# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
#
# This file is part of Hikari Command Handler.
#
# Hikari Command Handler is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari Command Handler is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari Command Handler. If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

import typing
import re

import hikari
from hikari.events import message

from handler import commands
from handler import context
from handler import errors
from handler import stringview

if typing.TYPE_CHECKING:
    from hikari.models import messages


class BotWithHandler(hikari.Bot):
    """
    A subclassed implementation of :class:`hikari.impl.bot.BotAppImpl` which contains a command handler.
    This should be instantiated instead of the superclass if you want to be able to use 
    the command handler implementation provided.

    Args:
        prefix (:obj:`str`): The bot's command prefix.
        ignore_bots (:obj:`bool`): Whether or not the bot should ignore its commands when invoked by other bots. Defaults to `True`
        **kwargs: Other parameters passed to the :class:`hikari.impl.bot.BotAppImpl` constructor.
    """

    def __init__(self, *, prefix: str, ignore_bots=True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_dispatcher.subscribe(message.MessageCreateEvent, self.handle)
        self.prefix = prefix
        self.ignore_bots = ignore_bots
        self.commands: typing.MutableMapping[str, commands.Command] = {}

    async def _default_command_error(self, event: errors.CommandErrorEvent):
        raise event.error

    def command(self, allow_extra_arguments=True):
        """
        A decorator that registers a callable as a command for the handler.

        Args:
            allow_extra_arguments (:obj:`bool`): Whether or not the handler should raise an error if a command is run with more arguments than it requires. Defaults to True.

        Example:

            .. code-block:: python

                bot = handler.Bot(token="token_here", prefix="!")

                @bot.command()
                async def ping(ctx):
                    await ctx.reply("Pong!")
        """
        registered_commands = self.commands

        def decorate(func: typing.Callable):
            nonlocal registered_commands
            nonlocal allow_extra_arguments
            if not registered_commands.get(func.__name__):
                registered_commands[func.__name__] = commands.Command(
                    func, allow_extra_arguments
                )

        return decorate

    def resolve_arguments(self, message: messages.Message) -> typing.List[str]:
        """
        Resolves the arguments that a command was invoked with from the message containing the invocation.

        Args:
            message (:obj:`hikari.models.messages.Message`): The message to resolve the arguments for.

        Returns:
            List[ :obj:`str` ] List of the arguments the command was invoked with.

        Note:
            The first item in the list will always contain the prefix+command string which can
            be used to validate if the message was intended to invoke a command and if the command
            they attempted to invoke is actually valid.
        """
        string_view = stringview.StringView(message.content)
        return string_view.deconstruct_str()

    async def handle(self, event: message.MessageCreateEvent) -> None:
        """
        The message listener that deals with validating the invocation messages. If invocation message
        is valid then it will invoke the relevant command. This will raise a ``CommandNotFound`` if the command
        attempted to be invoked does not exist.

        Args:
            event (:obj:`hikari.events.message.MessageCreateEvent`): The message create event containing a possible command invocation.

        Returns:
            ``None``

        Raises:
            :obj:`.errors.CommandNotFound`
        """
        if self.ignore_bots and event.message.author.is_bot:
            return

        if not event.message.content:
            return

        args = self.resolve_arguments(event.message)
        # Check if the message was actually a command invocation
        if not args[0].startswith(self.prefix):
            return

        invoked_with = args[0].replace(self.prefix, "")
        if invoked_with not in self.commands:
            self.event_dispatcher.dispatch(
                errors.CommandErrorEvent(
                    errors.CommandNotFound(invoked_with), event.message
                )
            )
            return
        invoked_command = self.commands[invoked_with]

        command_context = context.Context(
            event.message, self.prefix, invoked_with, invoked_command
        )

        if not invoked_command._has_max_args:
            await invoked_command(command_context, *args[1:])
        else:
            if len(args[1:]) < invoked_command._max_args:
                self.event_dispatcher.dispatch(
                    errors.CommandErrorEvent(
                        errors.NotEnoughArguments(invoked_with), event.message
                    )
                )
                return
            elif (
                len(args[1:]) > invoked_command._max_args
                and not invoked_command.allow_extra_arguments
            ):
                self.event_dispatcher.dispatch(
                    errors.CommandErrorEvent(
                        errors.TooManyArguments(invoked_with), event.message
                    )
                )
                return
            if invoked_command._max_args == 0:
                await invoked_command(command_context)
            else:
                await invoked_command(
                    command_context, *args[1 : invoked_command._max_args + 1]
                )

    def run(self) -> None:
        if errors.CommandErrorEvent not in self.event_dispatcher._listeners:
            self.event_dispatcher.subscribe(
                errors.CommandErrorEvent, self._default_command_error
            )
        super().run()
