[![PyPI](https://img.shields.io/pypi/v/hikari-lightbulb)](https://pypi.org/project/hikari-lightbulb)

# Lightbulb
Lightbulb is designed to be an easy-to-use command handler library that integrates with the
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
# Import the libraries
import hikari
import lightbulb

# Create a GatewayBot instance
bot = hikari.GatewayBot("your_token_here")
client = lightbulb.client_from_app(bot)
# Ensure the client starts once the bot is run
bot.subscribe(hikari.StartingEvent, client.start)

# Register the command with the client
@client.register()
class Ping(
    # Command type - builtins include SlashCommand, UserCommand, and MessageCommand
    lightbulb.SlashCommand,
    # Command declaration parameters
    name="ping",
    description="checks the bot is alive",
):
    # Define the command's invocation method. This method must take the context as the first
    # argument (excluding self) which contains information about the command invocation.
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
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
Pull requests are welcome. For major changes, please open an issue/discussion first to discuss what you would like to change.

Please try to ensure that documentation is updated if you add any features accessible through the public API.

If you use this library and like it, feel free to sign up to GitHub and star the project,
it is greatly appreciated and lets me know that I'm going in the right direction!

## Links
- **License:** [MIT](https://choosealicense.com/licenses/mit/)
- **Repository:** [GitHub](https://github.com/tandemdude/hikari-lightbulb)
- **Documentation:** [ReadTheDocs](https://hikari-lightbulb.readthedocs.io/en/latest/)

## IDE Plugin

Lightbulb now has a plugin for IntelliJ-based IDEs (IntelliJ, Pycharm, etc) to help improve the developer experience 
by providing autocompletion and type checking not yet supported by other tools. More features such as command 
boilerplate generation and further code inspections are planned.

You can install the plugin from the Jetbrains Marketplace within your IDE. View the plugin 
[here](https://plugins.jetbrains.com/plugin/24669-hikari-lightbulb-support).
