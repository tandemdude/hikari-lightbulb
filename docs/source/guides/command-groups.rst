=======================
Creating Command Groups
=======================

Command groups are a method of grouping commands to reduce the top-level clutter that could occur if your bot had a large
number of commands. For example, say you had three commands: ``setprefix``, ``setchannel``, ``setrole``. You can see how,
if your bot had a lot of configurable features, it could result in unnecessary clutter due to many similarly named commands.

Command groups are the solution to this problem, it allows you to have a single top-level command - ``set`` - which has
multiple subcommands that allow the user to set multiple bot configuration values. For example, the previously mentioned commands
would be changed into the following command tree:

.. code-block::

    set
    ├─ prefix
    ├─ channel
    ├─ role

These commands would be invoked using the names ``set prefix``, ``set channel`` and ``set role`` respectfully.

Command Group Support
=====================

Both prefix and slash commands support command groups, subgroups, and subcommands. However, for prefix commands, a given
command group can have an arbitrary number of levels subgroups and subcommands, whereas for slash commands you can only go
a maximum of three levels deep:

``group -> subgroup -> subcommand`` for slash commands

or

``group -> subgroup -> subgroup -> ... -> subcommand`` for prefix commands.

**Relevant API References:**

- :obj:`lightbulb.commands.prefix.PrefixCommandGroup`

- :obj:`lightbulb.commands.prefix.PrefixSubGroup`

- :obj:`lightbulb.commands.prefix.PrefixSubCommand`

- :obj:`lightbulb.commands.slash.SlashCommandGroup`

- :obj:`lightbulb.commands.slash.SlashSubGroup`

- :obj:`lightbulb.commands.slash.SlashSubCommand`

Lightbulb requires you to create a function for each command group and subgroup, but you should note that due to a discord limitation,
this function **will not** be run for slash commands as the root group/subgroup cannot be invoked for slash commands.

Creating a Command Group
========================

For this section we will be using prefix commands as an example, slash commands work in exactly the same way.

You define a command group exactly the same way that you would a normal command, however instead of providing ``lightbulb.PrefixCommand``
to the :obj:`lightbulb.decorators.implements` decorator, we will instead be providing ``lightbulb.PrefixCommandGroup``.

A basic example can be seen below:

.. code-block:: python

    import lightbulb

    bot = lightbulb.BotApp(..., prefix="!")

    @bot.command
    @lightbulb.command("foo", "test group")
    @lightbulb.implements(lightbulb.PrefixCommandGroup)
    async def foo(ctx: lightbulb.Context) -> None:
        await ctx.respond("invoked foo")

This command would be invoked like a normal prefix command and behaves like a normal prefix command - ``!foo``.

Adding Subcommands
==================

To add a subcommand to a given command group or subgroup you have to provide a subcommand class to the :obj:`lightbulb.decorators.implements`
decorator. In this case, that would be the class ``lightbulb.PrefixSubCommand``. Note that this only creates the command,
we still need to link it back to the group that it belongs to. To do this we use the :obj:`lightbulb.commands.base.CommandLike.child`
decorator as seen below.

.. code-block:: python

    import lightbulb

    bot = lightbulb.BotApp(..., prefix="!")

    @bot.command
    @lightbulb.command("foo", "test group")
    @lightbulb.implements(lightbulb.PrefixCommandGroup)
    async def foo(ctx: lightbulb.Context) -> None:
        await ctx.respond("invoked foo")

    @foo.child
    @lightbulb.command("bar", "test subcommand")
    @lightbulb.implements(lightbulb.PrefixSubCommand)
    async def bar(ctx: lightbulb.Context) -> None:
        await ctx.respond("invoked foo bar")

The subcommand ``bar`` would be invoked by first invoking its parent ``foo``, and then separating the invocation of
``bar`` using a space - ``!foo bar``.

Adding Subgroups
================

Adding subgroups to command groups (or other subgroups) is done exactly the same way that you would add a subcommand to
a given group. Similarly, adding subcommands to subgroups is identical to the method used to add subcommands to a top-level
command group.

See below for an example:

.. code-block:: python

    import lightbulb

    bot = lightbulb.BotApp(..., prefix="!")

    @bot.command
    @lightbulb.command("foo", "test group")
    @lightbulb.implements(lightbulb.PrefixCommandGroup)
    async def foo(ctx: lightbulb.Context) -> None:
        await ctx.respond("invoked foo")

    @foo.child
    @lightbulb.command("bar", "test subgroup")
    @lightbulb.implements(lightbulb.PrefixSubGroup)
    async def bar(ctx: lightbulb.Context) -> None:
        await ctx.respond("invoked foo bar")

    @bar.child
    @lightbulb.command("baz", "test subcommand")
    @lightbulb.implements(lightbulb.PrefixSubGroup)
    async def baz(ctx: lightbulb.Context) -> None:
        await ctx.respond("invoked foo bar baz")

In the above example, the command ``foo`` would be invoked using ``!foo``, the command ``bar`` would be invoked using
``!foo bar``, and the command ``baz`` would be invoked using ``!foo bar baz``.

Any command options for subcommands or subgroups **must** be provided after the full qualified name of the command or subcommand
being invoked.

Extra Information
=================

By default, subcommands and subcommand groups **will not** inherit the checks from the parent group or subgroup that the command
belongs to. This behaviour can be changed by providing the kwarg ``inherit_checks=True`` in the :obj:`lightbulb.decorators.command`
decorator.
