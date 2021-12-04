.. _getting-started:

===============
Getting Started
===============

Lightbulb can be installed using Python's pip:

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
    bot = lightbulb.BotApp(token="your_token_here", prefix="your_prefix_here")

    # Register the command to the bot
    @bot.command
    # Use the command decorator to convert the function into a command
    @lightbulb.command("ping", "checks the bot is alive")
    # Define the command type(s) that this command implements
    @lightbulb.implements(lightbulb.PrefixCommand)
    # Define the command's callback. The callback should take a single argument which will be
    # an instance of a subclass of lightbulb.Context when passed in
    async def ping(ctx: lightbulb.Context) -> None:
        # Send a message to the channel the command was used in
        await ctx.respond("Pong!")

    # Run the bot
    # Note that this is blocking meaning no code after this line will run
    # until the bot is shut off
    bot.run()

When this code is run, you will get some logging information and a Hikari banner printed across your
terminal. The bot will be online and you can test out the command!

.. note::
    You should note that the order that the decorators are applied is rather important. The ``lightbulb.implements``
    decorator should **always** be on the bottom of the stack, followed by the ``lightbulb.command`` decorator on top
    of it. The ``bot.command`` decorator **must** always be on the top of the stack if you are using it.

Optional: Setting up logging
============================

Lightbulb uses the ``logging`` library for the logging of useful information for debugging and testing purposes. For
example, if the logging level is set to debug, messages will be displayed every time a command, plugin or extension
is added or removed. This can be changed by using the ``logs`` argument if you want to keep the customization that
``hikari`` does by default. Alternatively, you can use ``logging`` directly.

Changing the logging level with using the ``logs`` argument:
::

    import logging
    import lightbulb

    # Set to debug for both lightbulb and hikari
    bot = lightbulb.BotApp(..., logs="DEBUG")

    bot.run()

Using different logging levels for both ``hikari`` and ``lightbulb``:
::

    import logging
    import lightbulb

    # Set different logging levels for both lightbulb and hikari
    bot = lightbulb.BotApp(
        ...,
        logs={
            "version": 1,
            "incremental": True,
            "loggers": {
                "hikari": {"level": "INFO"},
                "hikari.ratelimits": {"level": "TRACE_HIKARI"},
                "lightbulb": {"level": "DEBUG"},
            },
        },
    )

    bot.run()

.. note::
    Usually you should set the logging level to ``logging.INFO`` as setting it to debug can cause a lot
    of console spam, possibly impacting the performance of your program.
