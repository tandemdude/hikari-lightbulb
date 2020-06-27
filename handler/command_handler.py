import typing
import re

from hikari import Bot
from hikari.events import message
from hikari.models import messages

from handler import commands
from handler import context
from handler import errors
from handler import stringview


class BotWithHandler(Bot):
    def __init__(self, *, prefix: str, ignore_bots=True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_dispatcher.subscribe(message.MessageCreateEvent, self.handle)
        self.prefix = prefix
        self.ignore_bots = ignore_bots
        self.commands: typing.MutableMapping[str, commands.Command] = {}

    def command(self):
        registered_commands = self.commands

        def decorate(func: typing.Callable):
            nonlocal registered_commands
            if not registered_commands.get(func.__name__):
                registered_commands[func.__name__] = commands.Command.from_callable(
                    func
                )

        return decorate

    def resolve_arguments(self, message: messages.Message) -> typing.List[str]:
        string_view = stringview.StringView(message.content)
        return string_view.deconstruct_str()

    async def handle(self, event: message.MessageCreateEvent) -> None:
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
            raise errors.CommandNotFound(invoked_with)
        invoked_command = self.commands[invoked_with]

        command_context = context.Context(
            event.message, self.prefix, invoked_with, invoked_command
        )
        await invoked_command(command_context, *args[1:])

    async def default_command_error(self, event: errors.CommandErrorEvent):
        raise event.error

    def run(self):
        if errors.CommandErrorEvent not in self.event_dispatcher._listeners:
            self.event_dispatcher.subscribe(
                errors.CommandErrorEvent, self.default_command_error
            )
        super().run()
