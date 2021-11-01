==================================
Implementing a Custom Help Command
==================================

Naturally, you may find the default help command provided unappealing. It is due to this that you may, at some
point want to customise it to change its appearance or order of commands, etc.

Method 1: Manually Generated
============================

The easy way to go about creating your custom help command is by simply disabling the default one, and
creating a command named ``help`` and adding it to the bot yourself.

Example:
::

    import lightbulb
    from lightbulb import commands

    bot = lightbulb.BotApp(..., help_class=None)

    HELP_MESSAGE = """
    Commands Available:
    `foo` - does stuff
    `bar` - does other stuff
    `baz` - also does stuff
    """

    @bot.command
    @lightbulb.command("help", "Gets help for bot commands")
    @lightbulb.implements(commands.PrefixCommand)
    async def help(ctx):
        await ctx.respond(HELP_MESSAGE)

However, the main flaw of this method is that the command will not be auto generated so you will have to add details
for all of your commands, groups, and plugins manually.

Method 2: Automatically Generated
=================================

TODO
