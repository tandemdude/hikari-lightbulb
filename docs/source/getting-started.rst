===============
Getting Started
===============

Hikari Command Handler can be installed using Python's pip provided that you already have git installed:

``$ pip install git+https://gitlab.com/tandemdude/hikari-command-handler.git``

.. note::
    This library is dependent on Hikari and so naturally will only be available for Python
    versions that Hikari also supports.


Creating Your First Bot
=======================

Your first bot can be written in just a few lines of code:
::

    # Import the command handler
    import handler

    # Instantiate a Bot instance
    bot = handler.Bot(token="your_token_here", prefix="your_prefix_here")

    # Define a command using the bot.command decorator
    # Note that all commands must have the argument ctx which will be an instance
    # of the handler.context.Context class.
    @bot.command()
    async def ping(ctx):
        # Send a message to the channel the command was used in
        await ctx.reply("Pong!")

    # Run the bot
    # Note that this is blocking meaning no code after this line will run
    # until the bot is shut off
    bot.run()

When this code is run, you will get some logging information and a Hikari banner printed across your
terminal. The bot will be online and you can test out the command!