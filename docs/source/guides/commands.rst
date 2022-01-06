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

The :obj:`lightbulb.decorators.implements` decorator acts as the base for every command you will make using Lightbulb.

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

This decorator converts the decorated function into a :obj:`lightbulb.commands.base.CommandLike` object. This object
can be coerced into any of the command classes that Lightbulb supports.

Given the fundamental differences between slash commands and prefix commands, not all kwargs will affect all of the
command types that can be created.

**Positional Arguments:**

- ``name`` (required) - The name of the command. This will be the string used to invoke the command for prefix commands,
  for application commands it will be sent to discord when the command is created.

- ``description`` (required) - The command's description. This will show up beside the command name in the help command, and for slash
  commands it will be sent to discord when the command is created.

**Keyword Arguments:**

- ``aliases`` (optional) - A sequence of aliases to use for the command's name. These will also be able to invoke the command,
  but will only affect prefix commands. Application commands will not be aliased.

- ``guilds`` (optional) - A sequence of integer guild IDs that the command will be created in. This only affects application
  commands. If a value is not set then the value passed in to ``default_enabled_guilds`` when the bot was initialised will
  be used instead.

- ``parser`` (optional) - The argument parser to use for the prefix command implementation of this command.

- ``error_handler`` (optional) - The error handler function to use for all errors thrown by this command. This can also be
  set later using the :obj:`lightbulb.commands.base.CommandLike.set_error_handler` method. The error handler function should
  take a single argument ``event``, which will be an instance of the :obj:`lightbulb.events.CommandErrorEvent` event.

- ``auto_defer`` (optional) - Whether or not the response to the command should be automatically deferred on command invocation.
  If ``True``, then a response of type ``DEFERRED_MESSAGE_CREATE`` will be sent if the command was triggered by an interaction.
  For prefix commands, a typing indicator will be triggered in the channel the command was invoked in instead. Defaults to ``False``.

- ``ephemeral`` (optional) - Whether or not to send responses from the invocation of this command as ephemeral by
  default. If ``True`` then all responses from the command will use the flag :obj:`hikari.MessageFlags.EPHEMERAL`.
  This will not affect prefix commands as responses from prefix commands **cannot** be ephemeral. This can be overriden
  by supplying the kwarg ``flags=hikari.MessageFlags.NONE`` to your call to the ``respond`` method.

- ``hidden`` (optional) - Whether or not to hide the command from the help command. Defaults to ``False``.

- ``inherit_checks`` (optional) - Whether or not the command should inherit checks from the parent group. Naturally, this will
  only affect subgroups and subcommands. Defaults to ``False``.

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

**Positional args:**

- ``name`` (required): The name of the command option. This will be used as the identifier when getting the options
  from the invocation context, and will be send to discord for the creation of application commands.

- ``description`` (required): The description of the command option. This will also be send to discord
  during the creation of application commands.

- ``type`` (optional): The type of the option, or converter to use with the option for prefix commands. See the later
  section on converters for more information on the valid types. If not provided then the type defaults to ``str``.

**Keyword args:**

- ``required`` (optional): Boolean indicating whether or not the option is required. If not provided then it will be inferred
  from whether or not a default value was provided for this option. If this is explicitly ``True`` and no default was provided
  then the default value will be set to ``None``.

- ``choices`` (optional): Sequence of choices for the option. This only affects slash commands. If provided, must be a sequence
  containing items of the same type as the option's type (``str``, ``int``, or ``float``) or a sequence of :obj:`hikari.CommandChoice`
  objects. If not a sequence of ``CommandChoice`` objects, then the choice's name will be set to the string representation
  of the given value.

- ``channel_types`` (optional): Sequence of :obj:`hikari.ChannelType` that the option can accept. If provided then this option
  should be a type that coerces to ``hikari.OptionType.CHANNEL``. This only affects slash commands.

- ``default`` (optional): The default value for the option. If provided, this will set ``required`` to ``False``.

- ``modifier`` (optional): Modifier for the parsing of the option for prefix commands. Should be a value from the
  :obj:`lightbulb.commands.base.OptionModifier` enum. Modifiers are ``CONSUME_REST`` (consumes the rest of the argument
  string without parsing it) and ``GREEDY`` (consumes and converts arguments until either the argument string is exhausted
  or argument conversion fails).

- ``min_value`` (optional): The minimum value permitted for this option (inclusive). Only available if the option type
  is numeric (integer or float).

- ``max_value`` (optional): The maximum value permitted for this option (inclusive). Only available if the option type
  is numeric (integer or float).

**For example:**

.. code-block:: python

    import lightbulb

    @lightbulb.option("text", "text to repeat", modifier=commands.OptionModifier.CONSUME_REST)
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
