.. _custom-help:

==================================
Implementing a Custom Help Command
==================================

Naturally, you may find the default help command provided unappealing. It is due to this that you may, at some
point want to customise it to change its appearance or order of commands, etc.


Method 1: Manually Generated
============================

The easy way to go about creating your custom help command is by simply removing the default one, and
creating a command named ``help`` and adding it to the bot yourself.

Example:
::

    import lightbulb

    bot = lightbulb.Bot(...)
    bot.remove_command("help")

    HELP_MESSAGE = """
    Commands Available:
    `foo` - does stuff
    `bar` - does other stuff
    `baz` - also does stuff
    """

    @bot.command()
    async def help(ctx):
        await ctx.respond(HELP_MESSAGE)

However, the main flaw of this method is that the command will not be auto generated so you will have to add details
for all of your commands, groups, and plugins manually.


Method 2: Auto-Generated
========================

The other way to create your own help command is through subclassing :obj:`~lightbulb.help.HelpCommand` and overriding
the methods that send the help message.
::

    from lightbulb import help

    class CustomHelp(help.HelpCommand):
        async def object_not_found(self, context, name):
            # Override this method to change the message sent when help is
            # requested for an object that does not exist
            ...

        async def send_help_overview(self, context):
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

If you wish to make your help command loadable/unloadable you will need to put it into a plugin and optionally an extension.
The implementation for an extension could look something like below.
::

    class Help(lightbulb.Plugin):
        def __init__(self, bot):
            super().__init__()
            self.bot = bot
            self._original_help_command = bot.help_command
            bot.help_command = YourHelpCommandClass(bot)

        def plugin_remove(self):
            self.bot.help_command = self._original_help_command


    def load(bot):
        bot.add_plugin(Help(bot))

    def unload(bot):
        bot.remove_plugin("Help")

The help submodule also provides some useful utilities to help you with your implementation:

- :obj:`~lightbulb.help.get_help_text` - Gets the help text, pulled from the docstring of the command callback.

- :obj:`~.lightbulb.help.get_command_signature` - Gets the command signature, useful for displaying the usage of a command.

- :obj:`~lightbulb.help.filter_commands` - Filter a list of commands to remove any that the invoker of the help command cannot use.
