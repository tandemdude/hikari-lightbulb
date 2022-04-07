====================
Application Commands
====================

**What are application commands?**

In the words of discord:

"Application commands are commands that an application (bot) can register to Discord. They provide users a
first-class way of interacting directly with your application that feels deeply integrated into Discord."

Examples of application commands include:

- `Slash commands <https://discord.com/developers/docs/interactions/application-commands#slash-commands>`_

- `Message context menu commands (message commands) <https://discord.com/developers/docs/interactions/application-commands#message-commands>`_

- `User context menu commands (user commands) <https://discord.com/developers/docs/interactions/application-commands#user-commands>`_

**Important Information:**

As Discord has decided to ban bots from reading messages without the intent enabled, you should be using application commands wherever possible.

You should at least have a basic understanding of:

- interaction

- `global <https://discord.com/developers/docs/interactions/application-commands#making-a-global-command>`_ and
  `guild <https://discord.com/developers/docs/interactions/application-commands#making-a-guild-command>`_ commands

- the ``application.commands`` `OAuth scope <https://discord.com/developers/docs/interactions/application-commands#authorizing-your-application>`_

For an example slash command, see the `examples directory <https://github.com/tandemdude/hikari-lightbulb/tree/v2/examples>`_

.. warning::
    Note that by default, application commands will be **global** unless you specify a set of guilds that they should
    be created in (more on this below). Global commands **will** take up to one hour to sync to discord, so it is recommended that you use
    guild-specific commands during development and testing.

----

Creating a Basic Slash Command
==============================

Slash commands (and other application command types) are implemented exactly the same way as prefix commands. You just
replace the ``commands.PrefixCommand`` with ``commands.SlashCommand`` in the ``@lightbulb.implements`` decorator.

See Below
::

    import lightbulb

    bot = lightbulb.BotApp(...)

    @bot.command
    @lightbulb.command("ping", "checks that the bot is alive")
    @lightbulb.implements(lightbulb.SlashCommand)
    async def ping(ctx: lightbulb.Context) -> None:
        await ctx.respond("Pong!")

    bot.run()


Adding options to slash commands is also identical to how you add options to prefix commands
::

    import lightbulb

    bot = lightbulb.BotApp(...)

    @bot.command
    @lightbulb.option("text", "text to repeat")
    @lightbulb.command("echo", "repeats the given text")
    @lightbulb.implements(lightbulb.SlashCommand)
    async def echo(ctx: lightbulb.Context) -> None:
        await ctx.respond(ctx.options.text)

    bot.run()

To create message or user commands you need to add ``commands.MessageCommand`` and ``commands.UserCommand`` respectively
to the ``@lightbulb.implements`` decorator. You should note that message and user commands cannot take any options, however
the target of the command will **always** be stored in the option ``target``. Any option decorators added to context menu
commands will be ignored.

Setting Default Guilds
======================

Setting default guilds for a single command can be done using the ``guilds`` kwarg in the ``@lightbulb.command`` decorator
::

    import lightbulb

    bot = lightbulb.BotApp(...)

    @bot.command
    @lightbulb.command("hello", "Says hello", guilds=(123, 456))
    @lightbulb.implements(lightbulb.SlashCommand)
    async def echo(ctx: lightbulb.Context) -> None:
        await ctx.respond("Hi, this command only appears in guilds with ID 123 and 456.")

    bot.run()

Setting default guilds for commands in a ``lightbulb.Plugin`` can be done using the ``default_enabled_guilds`` kwarg in the
``lightbulb.Plugin`` constructor
::

    import lightbulb

    example = lightbulb.Plugin("Example", default_enabled_guilds=(123, 456))
    # All subsequent commands registered to this plugin will be guild commands

Setting default guilds for all commands at once can be done using the ``default_enabled_guilds`` kwarg in the ``BotApp`` constructor
::

    import lightbulb

    bot = lightbulb.BotApp(..., default_enabled_guilds=(123, 456))

    @bot.command
    @lightbulb.command("whoami", "Checks who you are")
    @lightbulb.implements(lightbulb.SlashCommand)
    async def ping(ctx: lightbulb.Context) -> None:
        await ctx.respond(ctx.author.username)

    bot.run()

Default Guild Resolution Order
==============================

When handling default guilds, lightbulb will resolve them in the following order:

- Command-specific default guilds (see :obj:`lightbulb.commands.base.CommandLike.guilds`)

- Plugin-specific default guilds (see :obj:`lightbulb.plugins.Plugin.default_enabled_guilds`)

- BotApp default guilds (see :obj:`lightbulb.app.BotApp.default_enabled_guilds`)

.. note::

    If the default guilds are set to an empty tuple or list for a command or plugin, then the
    command(s) will be global regardless of the downstream default guilds.
