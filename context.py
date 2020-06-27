from hikari.models import messages

from . import commands

class Context:
    def __init__(self, message: messages.Message, prefix: str, invoked_with: str, command: commands.Command):
        self.message: messages.Message = message
        self.prefix: str = prefix
        self.invoked_with: str = invoked_with
        self.command: commands.Command = command
