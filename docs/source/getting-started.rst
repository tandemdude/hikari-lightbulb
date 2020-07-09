===============
Getting Started
===============

Lightbulb can be installed using Python's pip provided that you already have git installed:

``$ pip install hikari-lightbulb``

.. note::
    This library is dependent on Hikari and so naturally will only be available for Python
    versions that Hikari also supports.


Creating Your First Bot
=======================

Your first bot can be written in just a few lines of code:
::

    # Import the command handler
    import lightbulb

    # Instantiate a Bot instance
    bot = lightbulb.Bot(token="your_token_here", prefix="your_prefix_here")

    # Define a command using the bot.command decorator
    # Note that all commands must have the argument ctx which will be an instance
    # of the lightbulb.context.Context class.
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


Optional: Setting up logging
============================

Lightbulb uses the ``logging`` library for the logging of useful information for debugging and testing purposes. For
example, if the logging level is set to debug, messages will be displayed every time a command, plugin or extension
is added or removed.

Example:
::

    import logging
    import lightbulb

    # Get the lightbulb logger and set the level to debug
    logging.getLogger("lightbulb").setLevel(logging.DEBUG)

    bot = lightbulb.Bot(...)

    bot.run()

This code sets the logging level of the lightbulb logger to debug. This will log all commands added or removed, plugins
added or removed, and extensions loaded or unloaded.

.. note::
    Usually you should set the logging level to ``logging.INFO`` as setting it to debug can cause a lot
    of console spam, possibly impacting the performance of your program.