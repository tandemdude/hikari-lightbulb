.. _commands-guide:

=================
Creating Commands
=================

You're using a command handler library so naturally you'll probably be wanting to make some commands for your bot.

If you haven't made your first command yet, it is recommended that you read the :ref:`getting-started` page before continuing.

.. note::
    You should note that the order that the decorators are applied is rather important. The ``lightbulb.implements``
    decorator should **always** be on the bottom of the stack, followed by the ``lightbulb.command`` decorator on top
    of it. The ``bot.command`` decorator **must** always be on the top of the stack if you are using it.

----

The Implements Decorator
========================

.. automodule:: lightbulb.decorators
    :members: implements
    :noindex:

This decorator acts as the base for every command you will make using Lightbulb.

It defines the type or multiple types of commands that the decorated callback function will implement.

**For example:**

.. code-block:: python

    import lightbulb

    @lightbulb.implements(lightbulb.PrefixCommand)
    async def foo(ctx: lightbulb.Context) -> None:
        # This command will be invoked using the command prefix(es) that the bot recognises.
        ...

    @lightbulb.implements(lightbulb.SlashCommand)
    async def bar(ctx: lightbulb.Context) -> None:
        # This command will be created as a slash command.
        ...

    @lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
    async def baz(ctx: lightbulb.Context) -> None:
        # This command will be able to be invoked both using the bot's command prefix(es),
        # and as a slash command using interactions.
        ...


----

The Command Decorator
=====================

.. automodule:: lightbulb.decorators
    :members: command
    :noindex:

This decorator converts the decorated function into a :obj:`lightbulb.commands.base.CommandLike` object. This object
can be coerced into any of the command classes that Lightbulb supports.

Given the fundamental differences between slash commands and prefix commands, not all kwargs will affect all of the
command types that can be created.

**For example:**

.. code-block:: python

    import lightbulb

    @lightbulb.command("foo", "test command", aliases=["bar", "baz"])
    @lightbulb.implements(lightbulb.PrefixCommand)
    async def foo(ctx: lightbulb.Context) -> None:
        ...

    @lightbulb.command("foo", "test slash command", guilds=[123453463456, 34569827369])
    @lightbulb.implements(lightbulb.SlashCommand)
    async def _foo(ctx: lightbulb.Context) -> None:
        ...


----

The Option Decorator
====================

Basic commands that respond with set messages are cool, but sometimes you might want to take input from
the user to allow you to create more complex commands and more complex flows.

Lightbulb provides the :obj:`lightbulb.decorators.option` decorator for this purpose.

.. automodule:: lightbulb.decorators
    :members: option
    :noindex:

**For example:**

.. code-block:: python

    import lightbulb

    @lightbulb.option("text", "text to repeat", modifier=lightbulb.OptionModifier.CONSUME_REST)
    @lightbulb.command("echo", "repeats the given text")
    @lightbulb.implements(lightbulb.PrefixCommand)
    async def echo(ctx: lightbulb.Context) -> None:
        await ctx.respond(ctx.options.text)


----

Converters and Slash Command Option Types
=========================================

Below is a list of all the acceptable types that you can pass into the ``type`` argument of the ``option`` decorator. On
the left is the type to pass in, the right side is the converter that the type is mapped to, or for slash commands,
the hikari ``OptionType`` that the type is mapped to.

**Prefix command converter mapping:**

Acceptable primitives: ``str``, ``int``, ``float``

- ``bool`` - :obj:`lightbulb.converters.special.BooleanConverter`

- ``hikari.User`` - :obj:`lightbulb.converters.special.UserConverter`

- ``hikari.Member`` - :obj:`lightbulb.converters.special.MemberConverter`

- ``hikari.GuildChannel`` - :obj:`lightbulb.converters.special.GuildChannelConverter`

- ``hikari.TextableGuildChannel`` - :obj:`lightbulb.converters.special.TextableGuildChannelConverter`

- ``hikari.TextableChannel`` - :obj:`lightbulb.converters.special.TextableGuildChannelConverter`

- ``hikari.GuildCategory`` - :obj:`lightbulb.converters.special.GuildCategoryConverter`

- ``hikari.GuildVoiceChannel`` - :obj:`lightbulb.converters.special.GuildVoiceChannelConverter`

- ``hikari.Role`` - :obj:`lightbulb.converters.special.RoleConverter`

- ``hikari.Emoji`` - :obj:`lightbulb.converters.special.EmojiConverter`

- ``hikari.Guild`` - :obj:`lightbulb.converters.special.GuildConverter`

- ``hikari.Message`` - :obj:`lightbulb.converters.special.MessageConverter`

- ``hikari.Invite`` - :obj:`lightbulb.converters.special.InviteConverter`

- ``hikari.Colour`` - :obj:`lightbulb.converters.special.ColourConverter`

- ``hikari.Color`` - :obj:`lightbulb.converters.special.ColourConverter`

- ``hikari.Snowflake`` - :obj:`lightbulb.converters.special.SnowflakeConverter`

- ``datetime.datetime`` - :obj:`lightbulb.converters.special.TimestampConverter`

- ``hikari.Attachment`` - No converter, attachment will be pulled from the message attachments.

**Slash command option type mapping:**

- ``str`` - ``hikari.OptionType.STRING``

- ``int`` - ``hikari.OptionType.INTEGER``

- ``float`` - ``hikari.OptionType.FLOAT``

- ``bool`` - ``hikari.OptionType.BOOLEAN``

- ``hikari.User`` - ``hikari.OptionType.USER``

- ``hikari.Member`` - ``hikari.OptionType.USER``

- ``hikari.GuildChannel`` - ``hikari.OptionType.CHANNEL``

- ``hikari.TextableGuildChannel`` - ``hikari.OptionType.CHANNEL``

- ``hikari.TextableChannel`` - ``hikari.OptionType.CHANNEL``

- ``hikari.GuildCategory`` - ``hikari.OptionType.CHANNEL``

- ``hikari.GuildVoiceChannel`` - ``hikari.OptionType.CHANNEL``

- ``hikari.Role`` - ``hikari.OptionType.ROLE``

- ``hikari.Emoji`` - ``hikari.OptionType.STRING``

- ``hikari.Guild`` - ``hikari.OptionType.STRING``

- ``hikari.Message`` - ``hikari.OptionType.STRING``

- ``hikari.Invite`` - ``hikari.OptionType.STRING``

- ``hikari.Colour`` - ``hikari.OptionType.STRING``

- ``hikari.Color`` - ``hikari.OptionType.STRING``

- ``hikari.Snowflake`` - ``hikari.OptionType.STRING``

- ``datetime.datetime`` - ``hikari.OptionType.STRING``

- ``hikari.Attachment`` - ``hikari.OptionType.ATTACHMENT``

.. note::
    Slash command options that resolve to type ``hikari.OptionType.STRING`` will also have the appropriate
    converter run upon invocation. If this causes the command to take too long to run then you can
    pass ``auto_defer=True`` to the ``lightbulb.command`` decorator. The deferral will be processed prior
    to the conversion of options.

----

Adding Checks to Commands
=========================

Checks prevent commands from being invoked if the user invoking the command does not meet the specified criteria. For
example, you can prevent commands from being used in DMs, restrict them to only the owner of the bot, or restrict commands
to only users that have specific permissions.

See :ref:`checks` for all of the checks that are provided by Lightbulb.

To add checks to a command, you need to use the :obj:`lightbulb.decorators.add_checks` decorator. The decorator takes
an arbitrary number of :obj:`lightbulb.checks.Check` objects and will add all of them to the command.

For example:

.. code-block:: python

    import lightbulb

    @lightbulb.add_checks(lightbulb.owner_only)
    @lightbulb.command("foo", "test command")
    @lightbulb.implements(lightbulb.PrefixCommand)
    async def foo(ctx: lightbulb.Context) -> None:
        await ctx.respond("You are the owner of this bot.")


You can also create custom checks by creating your own instance of the :obj:`lightbulb.checks.Check` class and passing
in your custom check function to the constructor. A check function should take a single argument, which will be the ``Context``
instance for the command that is attempting to be invoked. Your check should either raise an error or return ``False``
on failure and **must** return ``True`` if it passes. Your check may be a syncronous or asyncronous function.

For example:

.. code-block:: python

    import lightbulb

    # OPTIONAL: Converting the check function into a Check object
    @lightbulb.Check
    # Defining the custom check function
    def check_author_is_me(context: lightbulb.Context) -> bool:
        # Returns True if the author's ID is the same as the given one
        return context.author.id == 1455657467

    # Adding the check to a command
    @lightbulb.add_checks(check_author_is_me)
    # Or if you do not use the @lightbulb.Check decorator
    @lightbulb.add_checks(lightbulb.Check(check_author_is_me))


----

Adding Commands to the Bot
==========================

To add commands to the bot, you need to use the :obj:`lightbulb.app.BotApp.command` method, either as a
decorator, or by calling it with the :obj:`lightbulb.commands.base.CommandLike` object to add to the bot
as a command.

This method instantiates the different command objects for the given ``CommandLike`` object and registers
them to the correct bot attribute.

**For example:**

.. code-block:: python

    import lightbulb

    bot = lightbulb.BotApp(...)

    @bot.command  # valid
    @lightbulb.command("foo", "test command")
    @lightbulb.implements(lightbulb.PrefixCommand)
    async def foo(ctx: lightbulb.Context) -> None:
        ...

    @bot.command()  # also valid
    @lightbulb.command("bar", "test command")
    @lightbulb.implements(lightbulb.PrefixCommand)
    async def bar(ctx: lightbulb.Context) -> None:
        ...

    @lightbulb.command("baz", "test command")
    @lightbulb.implements(lightbulb.PrefixCommand)
    async def baz(ctx: lightbulb.Context) -> None:
        ...

    bot.command(baz)  # also valid
