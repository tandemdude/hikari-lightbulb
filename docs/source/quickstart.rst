.. _getting-started:

===============
Getting Started
===============

Lightbulb can be installed using pip:

``$ pip install hikari-lightbulb``

.. note::
    This library is dependent on Hikari and so naturally will only be available for Python
    versions that Hikari also supports.


Creating Your First Bot
=======================

Your first bot can be written in just a few lines of code:
::

    # Import the libraries
    import hikari
    import lightbulb

    # Create a GatewayBot instance
    bot = hikari.GatewayBot("your_token_here")
    client = lightbulb.client_from_app(bot)

    # Ensure the client will be started when the bot is ready
    bot.subscribe(hikari.StartedEvent, client.start)

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

When this code is run, you will get some logging information and a Hikari banner printed across your
terminal. The bot will be online and you can test out the command!

Optional: Setting up logging
============================

Lightbulb uses the ``logging`` library for the logging of useful information for debugging and testing purposes.
This can be changed by using the ``logs`` argument of the ``GatewayBot`` constructor. Alternatively, you can use
``logging`` directly.

Changing the logging level with using the ``logs`` argument:
::

    import logging
    import lightbulb

    # Set to debug for both lightbulb and hikari
    bot = hikari.GatewayBot(..., logs="DEBUG")
    ...

    bot.run()

Using different logging levels for both ``hikari`` and ``lightbulb``:
::

    import logging
    import lightbulb

    # Set different logging levels for both lightbulb and hikari
    bot = hikari.GatewayBot(
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
    ...

    bot.run()

.. note::
    Usually you should set the logging level to ``logging.INFO`` as setting it to debug can cause a lot
    of console spam, possibly impacting the performance of your program.
