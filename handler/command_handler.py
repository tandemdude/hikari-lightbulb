import typing
import re

from hikari import Bot
from hikari.events import message
from hikari.models import messages
from hikari.events import base

from handler import commands
from handler import context

ARGUMENT_REGEX = re.compile(r"(\".+\"|[^\s]+)")


class BotWithHandler(Bot):
    def __init__(self, prefix: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.event_dispatcher.subscribe(message.MessageCreateEvent, self.handle)
        self.prefix = prefix
        self.commands: typing.MutableMapping[str, commands.Command] = {}

    def command(self):
        commands = self.commands

        def decorate(func: typing.Callable):
            nonlocal commands
            if not commands.get(func.__name__):
                commands[func.__name__] = commands.Command.from_callable(func)

        return decorate

    def resolve_arguments(self, message: messages.Message) -> typing.List[str]:
        return ARGUMENT_REGEX.findall(message.content)

    async def handle(self, event: message.MessageCreateEvent) -> None:
        args = self.resolve_arguments(event.message)
        # Check if the message was actually a command invocation
        if not args[0].startswith(self.prefix):
            return

        invoked_with = args[0].replace(self.prefix, "")
        if invoked_with not in self.commands:
            return
        invoked_command = self.commands[invoked_with]

        command_context = context.Context(
            event.message, self.prefix, invoked_with, invoked_command
        )
        await invoked_command(command_context, *args[1:])
