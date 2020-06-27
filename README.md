# Simple command handler for hikari
**By yours truly (thomm.o)**

This is not installable through pip or anything at the moment so just download the project and dump the `handler` directory in the same place as your bot file.

Usage:
```python
import hikari
from hikari.events.message import MessageCreateEvent

import handler


bot = hikari.Bot(token="token_here")
cmd_handler = handler.Handler("test.")


@cmd_handler.command()
async def ping(ctx):
    await ctx.message.reply("Pong!")


@bot.listen(MessageCreateEvent)
async def on_message(event):
    await cmd_handler.handle(event.message)


bot.run()
```

TODO:
- Help command
- Other stuff to make it coolerer