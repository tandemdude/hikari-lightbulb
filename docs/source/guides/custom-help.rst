==================================
Implementing a Custom Help Command
==================================

Naturally, you may find the default help command provided unappealing. It is due to this that you may, at some
point want to customise it to change its appearance or order of commands, etc.

----

Method 1: Manually Generated
============================

The easy way to go about creating your custom help command is by simply disabling the default one, and
creating a command named ``help`` and adding it to the bot yourself.

Example:
::

    import lightbulb

    bot = lightbulb.BotApp(..., help_class=None)

    HELP_MESSAGE = """
    Commands Available:
    `foo` - does stuff
    `bar` - does other stuff
    `baz` - also does stuff
    """

    @bot.command
    @lightbulb.command("help", "Gets help for bot commands")
    @lightbulb.implements(lightbulb.PrefixCommand)
    async def help(ctx: lightbulb.Context) -> None:
        await ctx.respond(HELP_MESSAGE)

However, the main flaw of this method is that the command will not be auto generated so you will have to add details
for all of your commands, groups, and plugins manually.

----

Method 2: Automatically Generated
=================================

The other way to create your own help command is through subclassing :obj:`~lightbulb.help_command.BaseHelpCommand` and overriding
the methods that send the help message.
::

    import lightbulb

    class CustomHelp(lightbulb.BaseHelpCommand):
        async def send_bot_help(self, context):
            # Override this method to change the message sent when the help command
            # is run without any arguments.
            ...

        async def send_plugin_help(self, context, plugin):
            # Override this method to change the message sent when the help command
            # argument is the name of a plugin.
            ...

        async def send_command_help(self, context, command):
            # Override this method to change the message sent when the help command
            # argument is the name or alias of a command.
            ...

        async def send_group_help(self, context, group):
            # Override this method to change the message sent when the help command
            # argument is the name or alias of a command group.
            ...

        async def object_not_found(self, context, obj):
            # Override this method to change the message sent when help is
            # requested for an object that does not exist
            ...

If you wish to make your help command loadable/unloadable you will need to put it into an extension.
The implementation for an extension could look something like below.
::

    class YourHelpCommand(lightbulb.BaseHelpCommand):
        ...

    def load(bot):
        bot.d.old_help_command = bot.help_command
        bot.help_command = YourHelpComand(bot)

    def unload(bot):
        bot.help_command = bot.d.old_help_command
        del bot.d.old_help_command

The help submodule also provides some useful utilities to help you with your implementation:

- :obj:`~lightbulb.help_command.filter_commands` - Filter a list of commands to remove any that the invoker of the help command cannot use.
