from hikari.models import messages

from handler import commands


class Context:
    def __init__(
        self,
        message: messages.Message,
        prefix: str,
        invoked_with: str,
        command: commands.Command,
    ):
        self.message: messages.Message = message
        self.prefix: str = prefix
        self.invoked_with: str = invoked_with
        self.command: commands.Command = command

    async def reply(self, *args, **kwargs) -> messages.Message:
        return await self.message.reply(*args, **kwargs)
