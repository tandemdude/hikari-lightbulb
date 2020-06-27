import typing
import re
from hikari.models import messages

from .commands import Command
from . import context


ARGUMENT_REGEX = re.compile(r"(\".+\"|[^\s]+)")


class Handler:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.commands: typing.MutableMapping[str, Command] = {}

    def command(self):
        commands = self.commands

        def decorate(func: typing.Callable):
            nonlocal commands
            if not commands.get(func.__name__):
                commands[func.__name__] = Command.from_callable(func)

        return decorate

    def resolve_arguments(self, message: messages.Message) -> typing.List[str]:
        return ARGUMENT_REGEX.findall(message.content)

    async def handle(self, message: messages.Message):
        args = self.resolve_arguments(message)
        # Check if the message was actually a command invocation
        if not args[0].startswith(self.prefix):
            return

        invoked_with = args[0].replace(self.prefix, "")
        if invoked_with not in self.commands:
            return
        invoked_command = self.commands[invoked_with]

        command_context = context.Context(message, self.prefix, invoked_with, invoked_command)
        await invoked_command(command_context, *args[1:])
