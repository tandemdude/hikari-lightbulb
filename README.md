[![PyPI](https://img.shields.io/pypi/v/hikari-lightbulb)](https://pypi.org/project/hikari-lightbulb)

# Lightbulb
Lightbulb is designed to be an easy to use command handler library that integrates with the
Discord API wrapper library for Python, Hikari.

This library aims to make it simple for you to make your own Discord bots and provide
all the utilities and functions you need to help make this job easier.

## Installation
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install Lightbulb.

```bash
pip install hikari-lightbulb
```

## Usage
```python
# Import the command handler
import lightbulb

# Instantiate a Bot instance
bot = lightbulb.BotApp(token="your_token_here", prefix="your_prefix_here")

# Register the command to the bot
@bot.command
# Use the command decorator to convert the function into a command
@lightbulb.command("ping", "checks the bot is alive")
# Define the command type(s) that this command implements
@lightbulb.implements(lightbulb.PrefixCommand)
# Define the command's callback. The callback should take a single argument which will be
# an instance of a subclass of lightbulb.context.Context when passed in
async def ping(ctx: lightbulb.Context) -> None:
    # Send a message to the channel the command was used in
    await ctx.respond("Pong!")

# Run the bot
# Note that this is blocking meaning no code after this line will run
# until the bot is shut off
bot.run()
```

## Issues
If you find any bugs, issues, or unexpected behaviour while using the library,
you should open an issue with details of the problem and how to reproduce if possible.
Please also open an issue for any new features you would like to see added.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please try to update tests as appropriate and ensure that documentation is updated if
you add any features accessible through the public API.

If you use this library and like it, feel free to sign up to GitHub and star the project,
it is greatly appreciated and lets me know that I'm going in the right direction!

## Links
- **License:** [LGPLv3](https://choosealicense.com/licenses/lgpl-3.0/)
- **Repository:** [GitHub](https://github.com/tandemdude/hikari-lightbulb)
- **Documentation:** [ReadTheDocs](https://hikari-lightbulb.readthedocs.io/en/latest/)
