==============
Slash Commands
==============

Slash Commands Primer
=====================

As Discord has now decided to ban bots from reading messages without the intent enabled, you should now be using slash commands wherever possible.

Read more about this on the `discord documentation <https://discord.com/developers/docs/interactions/slash-commands>`_ yourself.

Creating Slash Commands
=======================

Your first slash command can be written very easily:
::

    # Import the command handler
    import lightbulb
    # Import the slash_commands submodule
    from lightbulb import slash_commands

    # Instantiate a Bot instance
    bot = lightbulb.Bot(token="your_token_here", prefix="your_prefix_here")

    # Create a custom slash command class and implement
    # the abstract methods
    class Echo(slash_commands.SlashCommand):
        @property
        def options(self):
            return [
                hikari.CommandOption(
                    name="text",
                    description="Text to repeat",
                    type=hikari.OptionType.STRING,
                    is_required=True
                ),
            ]

        @property
        def description(self):
            return "Repeats your input."

        @property
        def enabled_guilds(self):
            return None

        async def callback(self, context):
            await context.respond(context.options["text"].value)

    # Add the slash command to the bot
    bot.add_slash_command(Echo)
    # Run the bot
    # Note that this is blocking meaning no code after this line will run
    # until the bot is shut off
    bot.run()


API Reference
=============

.. automodule:: lightbulb.slash_commands
    :members:
    :show-inheritance:
    :member-order: bysource
