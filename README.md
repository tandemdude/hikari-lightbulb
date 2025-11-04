<p align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="/docs/source/_static/lightbulb_logo_dark.svg">
        <source media="(prefers-color-scheme: light)" srcset="/docs/source/_static/lightbulb_logo_light.svg">
        <img alt="Hikari-Lightbulb logo" src="https://raw.githubusercontent.com/tandemdude/hikari-lightbulb/refs/heads/master/docs/source/_static/lightbulb_logo_light.svg" width="50%">
    </picture>
</p>

[![PyPI](https://img.shields.io/pypi/v/hikari-lightbulb)](https://pypi.org/project/hikari-lightbulb)

# Overview
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

## Sponsors

I would like to give a special thanks to my sponsors for providing the funding to continue developing and improving
this resource over the past 5+ years.

- [nulldomain](https://github.com/null-domain)
- [Invite Tracker](https://invite-tracker.com)
- [Forbidden-A](https://github.com/Forbidden-A)

## Large Bots

The following large bots are all using Lightbulb in production:

<table>
    <tbody>
        <tr>
            <td align="center" valign="top" width="14.28%"><a href="https://invite-tracker.com"><img src="https://invite-tracker.com/og/invitetracker_logo.png" width="100px;" height="100px;" alt="Invite Tracker"/><br /><sub><b>Invite Tracker</b></sub></a></td>
            <td align="center" valign="top" width="14.28%"><a href="https://nmarkov.xyz"><img src="https://nmarkov.xyz/logo.png" width="100px;" height="100px;" alt="nMarkov"/><br /><sub><b>nMarkov</b></sub></a></td>
        </tr>
    </tbody>
</table>

Do you own a large bot using Lightbulb? Mention `@thomm.o` on [Discord](https://discord.gg/hikari) or submit a pull request to add your bot to the list!

## Show your Support

We love people's support in growing and improving. Be sure to leave a ⭐️ if you like the project, and I would gladly welcome
any contributions if you're interested!

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
