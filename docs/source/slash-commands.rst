==============
Slash Commands
==============

Slash Commands Primer
=====================

As Discord has now decided to ban bots from reading messages without the intent enabled, you should now be using `slash commands <https://discord.com/developers/docs/interactions/application-commands#slash-commands>`_ wherever possible.

Read more about this on the `discord documentation <https://discord.com/developers/docs/interactions/application-commands>`_ yourself.

You should at least have a basic idea of:

- interactions
- `global <https://discord.com/developers/docs/interactions/application-commands#making-a-global-command>`_ & `guild <https://discord.com/developers/docs/interactions/application-commands#making-a-guild-command>`_ commands
- the ``applications.commands`` `OAuth scope <https://discord.com/developers/docs/interactions/application-commands#authorizing-your-application>`_

----

For example slash command code see the `examples directory <https://github.com/tandemdude/hikari-lightbulb/tree/development/examples>`_

Creating a Basic Slash Command
==============================

Your first slash command can be written very easily:
::

    # Import the command handler
    import lightbulb

    # Instantiate a Bot instance
    bot = lightbulb.Bot(token="your_token_here", prefix="your_prefix_here")


    # Create a custom slash command class and implement
    # the abstract methods
    class Echo(lightbulb.SlashCommand):
        description = "Repeats your input."
        # Options
        text: str = lightbulb.Option("Text to repeat")

        async def callback(self, context):
            await context.respond(context.options.text)


    # Add the slash command to the bot
    bot.add_slash_command(Echo)
    # Run the bot
    # Note that this is blocking meaning no code after this line will run
    # until the bot is shut off
    bot.run()


----

Creating a Slash Command Group
==============================

Creating a slash command group is very similar to creating a normal slash command in that all it requires is for you to
create your own subclass of the base class :obj:`~lightbulb.slash_commands.SlashCommandGroup` and implement all the
required abstract methods.

To add a subcommand to your group, you must create your own subclass of the base class
:obj:`~lightbulb.slash_commands.SlashSubCommand` and, as you've probably guessed, implement all the required
abstract methods. In order to link it to the slash command group, you must decorate the subcommand with the decorator
:obj:`~lightbulb.slash_commands.SlashCommandGroup.subcommand`. An example can be seen below of a very simple
slash command group:
::

    # Import the command handler
    import lightbulb

    # Instantiate a Bot instance
    bot = lightbulb.Bot(token="your_token_here", prefix="your_prefix_here")


    class Foo(lightbulb.SlashCommandGroup):
        description = "Test slash command group."


    @Foo.subcommand()
    class Bar(lightbulb.SlashSubCommand):
        description = "Test subcommand."
        # Options
        baz: str = lightbulb.Option("Test subcommand option.")

        async def callback(self, context):
            await context.respond(context.options.baz)


----

Creating a Slash Command Subgroup
=================================

To create a slash command subgroup, you must first create a slash command group as seen in the previous
section. The :obj:`~lightbulb.slash_commands.SlashCommandGroup` class provides a ``subgroup`` decorator that
should be used in place of the ``subcommand`` decorator when adding a subgroup to the parent group. The subgroup
should inherit from the :obj:`~lightbulb.slash_commands.SlashSubGroup` base class.

Adding a subcommand to the subgroup is the exact same as adding a subcommand to the parent group as was seen in the
stage above. Below is a simple example of a subgroup implementation, with some of the implementation left out
as you may refer to the previous sections for more details.
::

    # Import the command handler
    import lightbulb

    # Instantiate a Bot instance
    bot = lightbulb.Bot(token="your_token_here", prefix="your_prefix_here")


    class Foo(lightbulb.SlashCommandGroup):
        ...


    @Foo.subgroup()
    class Bar(lightbulb.SlashSubGroup):
        description = "Test subgroup."


    @Bar.subcommand()
    class Baz(lightbulb.SlashSubCommand):
        ...


----

Slash Command Option Typehints
==============================

The defining of slash command options uses type-hinting in order to infer the type to send discord. All the
permitted types can be seen below. Note that if you wrap the type in a ``typing.Optional`` then the option
will be set as not-required unless specified otherwise in the associated :obj:`~lightbulb.slash_commands.Option` object.

Example:

.. code-block:: python

    text: str = Option("string option")
    number: typing.Optional[int] = Option("non-required integer option")
    user: hikari.User = Option("user option")
    choice: str = Option("option with choices", choices=["foo", "bar", "baz"])
    foo: typing.Optional[str] = Option("option with default", default="foo")

Permitted types:

- ``str`` (:obj:`hikari.OptionType.STRING`)
- ``int`` (:obj:`hikari.OptionType.INTEGER`)
- ``bool`` (:obj:`hikari.OptionType.BOOLEAN`)
- ``float`` (:obj:`hikari.OptionType.FLOAT`)
- ``hikari.User`` (:obj:`hikari.OptionType.USER`)
- ``hikari.TextableChannel`` (:obj:`hikari.OptionType.CHANNEL`)
- ``hikari.Role`` (:obj:`hikari.OptionType.ROLE`)
- ``hikari.Snowflake`` (:obj:`hikari.OptionType.MENTIONABLE`)

.. seealso::
    Discord's `documentation <https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-option-type>`_ on command option types.

----

Slash Command Checks
====================

You can use some of the lightbulb built-in checks with slash commands. Only the ``SlashCommand`` and ``SlashSubCommand``
classes support checks. The checks will be run prior to the command's callback being invoked and, similar to message command
checks, will raise a :obj:`~lightbulb.errors.CheckFailure`` exception if they do not pass. Checks are defined as
a sequence of :obj:`~lightbulb.checks.Check` objects defined in the slash command class as seen below.
::

    import lightbulb

    class OwnerOnlySlashCommand(lightbulb.SlashCommand):
        name = "foo"
        description = "bar"
        # Defining the list of checks
        # You can use any built-in checks, as long as it is explicitly
        # stated in the docstring that slash commands are supported.
        # You can also use custom checks by wrapping the check function
        # in a Check object
        checks = [
            lightbulb.owner_only,  # built-in check
            lightbulb.Check(some_check_function),  # custom check
        ]

----

Slash Command Cooldowns
=======================

It is very easy to implement cooldowns for your slash commands. All you need to do is assign a cooldown manager
to the class variable ``cooldown_manager``. All of lightbulb's built-in cooldown buckets work with slash commands.
::

    import lightbulb

    class Foo(lightbulb.SlashCommand):
        ...
        # Static cooldown
        cooldown_manager = lightbulb.CooldownManager(5, 1, lightbulb.UserBucket)
        # Dynamic cooldown
    cooldown_manager = lightbulb.CooldownManager(callback=some_function_that_returns_a_Bucket)

----

API Reference
=============

.. error::
    The inclusion of slash commands within a Plugin class is not supported.

Top level classes
=================

.. automodule:: lightbulb.slash_commands
    :members: Option, SlashCommand, SlashCommandGroup, SlashSubGroup, SlashSubCommand, SlashCommandContext, SlashCommandOptionsWrapper
    :show-inheritance:

Template classes
================

.. automodule:: lightbulb.slash_commands
    :members: BaseSlashCommand, WithAsyncCallback, WithGetCommand, WithCreationMethods, WithGetOptions, WithAsOption
    :show-inheritance:

Appendix
========

The method hikari-lightbulb uses for defining slash commands is very different to the method used to
define message/prefix commands. If you would prefer to use a similar decorator-chain definition style for
slash commands then you can use `filament <https://filament.readthedocs.io/en/latest/api-reference.html#module-filament.slash_commands>`_.

A short filament example can be seen below:

.. code-block:: python

    import filament
    import lightbulb

    bot = lightbulb.Bot(...)

    @filament.with_option(type=str, name="text", description="the text to repeat")
    @filament.slash_command(description="repeats your input")
    async def echo(context: lightbulb.SlashCommandContext) -> None:
        await context.respond(context.options.text)

    bot.add_slash_command(echo)
    bot.run()

As far as the bot is concerned, filament slash commands are functionally identical to slash commands defined
through the normal method that hikari-lightbulb provides, so everything you can do with hikari-lightbulb slash
commands can also be done with filament slash commands.

There is however, one notable exception to this rule in that filament slash commands cannot be detected
when using :obj:`lightbulb.command_handler.Bot.autodiscover_slash_commands`. If using filament slash commands,
you should instead use `filament's autodiscovery function <https://filament.readthedocs.io/en/latest/api-reference.html#filament.slash_commands.autodiscover_slash_commands>`_.
