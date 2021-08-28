==============
Slash Commands
==============

Slash Commands Primer
=====================

As Discord has now decided to ban bots from reading messages without the intent enabled, you should now be using slash commands wherever possible.

Read more about this on the `discord documentation <https://discord.com/developers/docs/interactions/application-commands>`_ yourself.

----

Creating a Basic Slash Command
==============================

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
    # Import the slash_commands submodule
    from lightbulb import slash_commands

    # Instantiate a Bot instance
    bot = lightbulb.Bot(token="your_token_here", prefix="your_prefix_here")


    class Foo(slash_commands.SlashCommandGroup):
        @property
        def description(self):
            return "Test slash command group."

        @property
        def enabled_guilds(self):
            return None


    @Foo.subcommand()
    class Bar(slash_commands.SlashSubCommand):
        @property
        def description(self):
            return "Test subcommand."

        @property
        def options(self):
            return [
                hikari.CommandOption(
                    name="baz",
                    description="Test subcommand option.",
                    is_required=True,
                    type=hikari.OptionType.STRING,
                )
            ]

        async def callback(self, context):
            await context.respond(context.options["baz"].value)


----

Creating a Slash Command Subgroup
=================================

To create a slash command subgroup, you must first create a slash command group as seen in the previous
section. The :obj`~lightbulb.slash_commands.SlashCommandGroup` class provides a ``subgroup`` decorator that
should be used in place of the ``subcommand`` decorator when adding a subgroup to the parent group. The subgroup
should inherit from the :obj:`~lightbulb.slash_commands.SlashSubGroup` base class.

Adding a subcommand to the subgroup is the exact same as adding a subcommand to the parent group as was seen in the
stage above. Below is a simple example of a subgroup implementation, with some of the implementation left out
as you may refer to the previous sections for more details.
::

    # Import the command handler
    import lightbulb
    # Import the slash_commands submodule
    from lightbulb import slash_commands

    # Instantiate a Bot instance
    bot = lightbulb.Bot(token="your_token_here", prefix="your_prefix_here")


    class Foo(slash_commands.SlashCommandGroup):
        ...


    @Foo.subgroup()
    class Bar(slash_commands.SlashSubGroup):
        @property
        def description(self):
            return "Test subgroup."


    @Bar.subcommand()
    class Baz(slash_commands.SlashSubCommand):
        ...


----

API Reference
=============

.. automodule:: lightbulb.slash_commands
    :members:
    :show-inheritance:
    :member-order: bysource
