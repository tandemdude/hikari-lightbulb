# Simple command handler for hikari
**By yours truly (thomm.o)**

This is not installable through pip or anything at the moment so just download the project and dump the `handler` directory in the same place as your bot file.

Usage:
```python
import handler

bot = handler.Bot(token="token_here", prefix="test.")

@bot.command()
async def ping(ctx):
    await ctx.message.reply("Pong!")

bot.run()
```

TODO:
- Help command
- Other stuff to make it coolerer