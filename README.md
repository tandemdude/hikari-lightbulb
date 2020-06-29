# Simple command handler for hikari
**By yours truly (thomm.o)**

## Installation

`$ pip install hikari-lightbulb`

## Usage

```python
import lightbulb

bot = lightbulb.Bot(token="token_here", prefix="test.")

@bot.command()
async def ping(ctx):
    await ctx.message.reply("Pong!")

bot.run()
```

[Documentation](https://tandemdude.gitlab.io/lightbulb)