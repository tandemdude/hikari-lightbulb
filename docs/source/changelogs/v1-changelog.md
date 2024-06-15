(v1-changelog)=
# Version 1 Changelog

Below are all the changelogs for the stable versions of hikari-lightbulb (version 1.0.0 to 1.5.2).

---

## Version 1.5.2

- Add `lightbulb.utils.nav.ButtonNavigator`.
- Add `lightbulb.utils.nav.ComponentButton`.
- Add `lightbulb.utils.permissions.permissions_for`.
- Add `lightbulb.utils.permissions.permissions_in`.
- Add `lightbulb.command_handler.Bot.app`.
- Rename `lightbulb.utils.nav.Navigator` to `lightbulb.utils.nav.ReactionNavigator`.
- Rename `lightbulb.utils.nav.NavButton` to `lightbulb.utils.nav.ReactionButton`.
- Implement cooldowns for slash commands. See `lightbulb.slash_commands.WithChecks.cooldown_manager`

## Version 1.5.1

- Fix annotations bug preventing invocation of the default help command.
- Fix bug if slash command `enabled_guilds` is set to `None`
- Add `lightbulb.converters.timestamp_converter` for converting timestamp mentions into datetime objects.
- Add `lightbulb.command_handler.Bot.default_enabled_guilds`.
- Add `lightbulb.commands.typing_override`.

## Version 1.5.0

- Add support for python `3.10`.
- Add `lightbulb.slash_commands.SlashCommandContext.fetch_response`.
- Add `lightbulb.command_handler.Bot.autodiscover_slash_commands` and `lightbulb.command_handler.Bot.autoremove_slash_commands`.
- Add slash command setup error message if it seems like the bot wasn't invited to guilds with the `application.commands` scope.
- Add `lightbulb.command_handler.Bot.load_extensions_from`, `lightbulb.command_handler.Bot.unload_extensions`, `lightbulb.command_handler.Bot.unload_all_extensions`, `lightbulb.command_handler.Bot.reload_extensions`, and `lightbulb.command_handler.Bot.reload_all_extensions`.
- Change `lightbulb.slash_commands.SlashCommandContext.respond` to always return the message object for the response.
- Change slash command setup logging message level to `INFO`.
- Change `lightbulb.utils.nav.Navigator` to work with slash commands.
- Converters for prefix/message commands now work if you are using `from __future__ import annotations`.
- Deprecate `lightbulb.utils.nav.StringNavigator` and `lightbulb.utils.nav.EmbedNavigator` in favour of `lightbulb.utils.nav.Navigator`.

## Version 1.4.0

**Breaking Changes**

- Replace all context mention attributes with `mentions`, returning a `hikari.Mentions` object.
- Replace `lightbulb.slash_commands.SlashCommandContext.options` with `lightbulb.slash_commands.SlashCommandContext.raw_options`
- Replace `lightbulb.slash_commands.SlashCommandContext.option_values` with `lightbulb.slash_commands.SlashCommandContext.options`
- Remove all deprecated functions and methods.

**Other Changes**

- Add ability to specify defaults for slash command options.
- Add dark mode to documentation.
- `lightbulb.slash_commands.SlashCommandContext.respond` now calls `lightbulb.slash_commands.SlashCommandContext.followup` if `create_initial_response` has already been called.
- Fix various docstrings and typos.

## Version 1.3.1

- Fix `has_roles` check not working.
- Fix `token` not being able to be passed positionally to the bot constructor.
- Export all objects in `lightbulb.slash_commands` to the top level. E.g. `lightbulb.slash_commands.SlashCommand -> lightbulb.SlashCommand`.
- Add `lightbulb.slash_commands.SlashCommandContext.is_initial_response` attribute.
- Add `lightbulb.slash_commands.SlashCommandContext.followup` method.
- Add `add_to_command_hook` parameter to `lightbulb.checks.Check`.
- Add more slash command events, `lightbulb.events.SlashCommandInvocationEvent`, `lightbulb.events.SlashCommandCompletionEvent`.

## Version 1.3.0

**Breaking changes**

- Reimplement checks, remove all decorators apart from `@lightbulb.check`.

**Other changes**

- Implement checks for slash commands.
- Implement error handling for slash commands, see `lightbulb.events.SlashCommandErrorEvent`.

## Version 1.2.6

- Add ability to define choices for slash command options.
- Fix permission checks not working as expected (again).
- Fix modification detection for global slash commands not working correctly.

## Version 1.2.5

- Fix slash command groups all sharing the same subcommands.
- Fix plugin_check not being applied to subcommands.
- Swap order of command checks and argument parsing - checks are now evaluated before arguments are parsed.

## Version 1.2.4

- Deprecate context properties and replace with cache getter methods.
- Fix permission checks not working as expected.
- Fix NameError and TypeError when attempting to add slash commands in python 3.9.

## Version 1.2.3

- Fix incorrect ordering of command options when being sent to discord.
- Fix optional arguments being required and required arguments being optional.

## Version 1.2.2

- Reimplemented slash commands to improve construction of slash command classes. See the documentation for more information.
- Fixed incorrect error being raised by `bot_has_permissions`

## Version 1.2.1

- Made the bot now only send a slash command create request to discord if it detects that the version discord holds is out of date. This can be disabled using the `recreate_changed_slash_commands` flag in the bot constructor.
- Various documentation improvements.

## Version 1.2.0

- Made the `bot` attribute of slash commands public.
- Added `lightbulb.slash_commands.SlashCommandContext.option_values`.
- Added `lightbulb.slash_commands.SlashCommandOptionsWrapper`.
- Added `lightbulb.command_handler.Bot.purge_slash_commands`.
- Added support for calling `lightbulb.command_handler.Bot.add_plugin` with a plugin class instead of an instance.
- Added ability for a bot to be slash commands only by passing the `slash_commands_only` flag into the constructor.
- Fixed `AttributeError` when using navigators.

## Version 1.1.0

- Implemented support for slash commands.

## Version 1.0.1

- Fixed `AttributeError` when using `lightbulb.command_handler.when_mentioned_or`.

## Version 1.0.0

**Stable Release**

- Compatibility with hikari 2.0.0dev101.
