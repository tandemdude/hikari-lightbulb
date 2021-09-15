===================
Version 1 Changelog
===================

Below are all the changelogs for the stable versions of hikari-lightbulb (version 1.0.0 to present).

----

Version 1.2.6
=============

- Added ability to define choices for slash command options.

Version 1.2.5
=============

- Fix slash command groups all sharing the same subcommands.

- Fix plugin_check not being applied to subcommands.

- Swap order of command checks and argument parsing - checks are now evaluated before arguments are parsed.

Version 1.2.4
=============

- Deprecate context properties and replace with cache getter methods.

- Fix permission checks not working as expected.

- Fix NameError and TypeError when attempting to add slash commands in python 3.9.

Version 1.2.3
=============

- Fix incorrect ordering of command options when being sent to discord.

- Fix optional arguments being required and required arguments being optional.

Version 1.2.2
=============

- Reimplemented slash commands to improve construction of slash command classes. See the documentation for more information.

- Fixed incorrect error being raised by ``bot_has_permissions``

Version 1.2.1
=============

- Made the bot now only send a slash command create request to discord if it detects that the version discord holds is out of date. This can be disabled using the ``recreate_changed_slash_commands`` flag in the bot constructor.

- Various documentation improvements.

Version 1.2.0
=============

- Made the ``bot`` attribute of slash commands public.

- Added :obj:`~lightbulb.slash_commands.SlashCommandContext.option_values`.

- Added :obj:`~lightbulb.slash_commands.SlashCommandOptionsWrapper`.

- Added :obj:`~lightbulb.command_handler.Bot.purge_slash_commands`.

- Added support for calling :obj:`~lightbulb.command_handler.Bot.add_plugin` with a plugin class instead of an instance.

- Added ability for a bot to be slash commands only by passing the ``slash_commands_only`` flag into the constructor.

- Fixed ``AttributeError`` when using navigators.

Version 1.1.0
=============

- Implemented support for slash commands.


Version 1.0.1
=============

- Fixed ``AttributeError`` when using :obj:`~lightbulb.command_handler.when_mentioned_or`.

Version 1.0.0
=============

**Stable Release**

- Compatibility with hikari 2.0.0dev101.
