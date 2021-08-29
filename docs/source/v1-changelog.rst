===================
Version 1 Changelog
===================

Below are all the changelogs for the stable versions of hikari-lightbulb (version 1.0.0 to present).

----

Version 1.2.0
=============

- Made the ``bot`` attribute of slash commands public.

- Added :obj:`~lightbulb.slash_commands.SlashCommandContext.option_values`.

- Added :obj:`~lightbulb.slash_commands.SlashCommandOptionsWrapper`.

- Added :obj:`~lightbulb.command_handler.Bot.purge_slash_commands`.

- Added support for calling :obj:`~lightbulb.command_handler.Bot.add_plugin` with a plugin class instead of an instance.


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

- From now on the project will use semantic versioning.
