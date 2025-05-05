(v0-changelog)=
# Pre-Release Changelog

Below are all the changelogs for the pre-release versions of hikari-lightbulb (version 0.0.38 to 0.0.61).

---

## Version 0.0.61

**Breaking Changes**

- Removed `ArgInfo` dataclass.
- Rewritten `lightbulb.commands.SignatureInspector` class.
- `lightbulb.command_handler.Bot.resolve_args_for_command` now takes an additional argument `context`.
- Calling `lightbulb.commands.Command.invoke` will no longer process converters.
- Changed `lightbulb.cooldowns.CooldownManager.add_cooldown` into a coroutine.

**Other Changes**

- Added `lightbulb.checks.has_attachment`.
- Added `lightbulb.checks.check_exempt`.
- Fixed `KeyError` being raised when attempting to remove a command/plugin that doesn't exist
- Created class mapping for converters. See `converters` for details.
- Added support for custom cooldowns through the `lightbulb.cooldowns.dynamic_cooldown` decorator.
- Added `lightbulb.converters.Greedy` converter.

## Version 0.0.60

- Added `lightbulb.events.LightbulbEvent.bot` property.
- Fixed admin permission checks not working as expected.

## Version 0.0.59

**Breaking Changes**

- `lightbulb.plugins.Plugin.commands` changed to a `set` from a `dict` for consistency.

**Other Changes**

- Added `lightbulb.plugins.Plugin.walk_commands`.

## Version 0.0.58

**Breaking Changes**

- `lightbulb.context.Context.reply` renamed to `lightbulb.context.Context.respond` for consistency with hikari.

**Other Changes**

- Fix `IndexError` raised when no command provided after the prefix.
- Fix `lightbulb.checks.human_only` and add `lightbulb.checks.webhook_only`.
- Fix `lightbulb.converters.role_converter` incorrectly converting from mentions.
- Include support for hikari `2.0.0.dev98`.

## Version 0.0.57

- Add `missing_args` parameter to `lightbulb.errors.NotEnoughArguments`.
- Fix `__iter__` for `lightbulb.converters.WrappedArg`.
- Improve `lightbulb.command_handler.Bot.get_command` to allow you to get subcommands without having to call `lightbulb.commands.Group.get_subcommand`.

## Version 0.0.56

- Move docs to [readthedocs](https://hikari-lightbulb.readthedocs.io/en/latest/).
- Refactor errors to ensure they get instantiated correctly everywhere they are used.
- Fix various check messages and an issue where a check decorator added an incorrect check function.

## Version 0.0.55

- Fix issue with errors not being raised correctly.
- Fix `lightbulb.help.get_command_signature` showing ctx for subcommands.
- Make `lightbulb.checks.bot_has_guild_permissions` and `lightbulb.checks.has_guild_permissions` pass if bot or invoker has the administrator permission.

## Version 0.0.54

- Various performance improvements.

## Version 0.0.53

- Fix print_banner.
- Bump requirements.

## Version 0.0.52

**Breaking changes**

- Removed custom_emoji_converter and replaced it with `.converters.emoji_converter`.

**Other changes**

- Added `.checks.has_permissions` and `.checks.bot_has_permissions`.
- Added `.converters.guild_converter`.
- Exposed navigator callbacks to make it easier to supply your own buttons.
- Fixed navigator not working with custom emojis when using your own buttons.

## Version 0.0.51

- Added support for hikari 2.0.0.dev85.

## Version 0.0.50

- Fixed `.context.channel`.
- Added NSFW channel only check.
- Ensured all docstrings are correct and up to date, including any examples.

## Version 0.0.49

- Improved help docstring format parsing.
- Fixed `.help.get_command_signature` no longer working due to an `AttributeError`.
- Fixed `.command_handler.Bot.send_help` no longer working.

## Version 0.0.48

- Added `.converters.colour_converter` and `.converters.message_converter`.
- Added support for `typing.Union` and `typing.Optional` as converters/typehints.
- Exposed the current help class the bot uses through {attr}`~.command_handler.Bot.help_command`.
- Added support for a custom cooldown manager class through the `.cooldowns.cooldown` decorator.
- Improved the error message for `.errors.CommandInvocationError`.

## Version 0.0.47

- Added `.context.Context.channel` and `.context.Context.guild` properties.
- Added `.plugins.Plugin.plugin_check` method.
- Added `.converters.custom_emoji_converter`.
- Made converters work when the arg is a name/name#discrim/nickname/etc
- Added support for hikari 2.0.0.dev75

## Version 0.0.46

- Fixed converters not working with kwargs for commands in plugins.
- Improved README.md.
- Added documentation and public method for how to customise how arguments are parsed.

## Version 0.0.45

- Rewrote the argument parsing system and greedy arg system.
- Made converters work for greedy args.
- Added functionality to `.stringview.StringView` to allow it to only parse up to a specified number of args.
- Abstracted the `.command_handler.Bot.handle` method to make it easier to override to customise functionality.

## Version 0.0.44

- Improved `.command_handler.Bot.walk_commands`.
- Added `.commands.Group.walk_commands`.
- Added `.commands.Command.qualified_name`, `.commands.Command.callback`, `.commands.Command.checks`.
- Fixed wonky default help for command groups.
- Added `.context.Context.send_help` and `.command_handler.Bot.send_help`.
- Added `.command_handler.Bot.get_context`.
- Added `.command_handler.Bot.help_class`.

## Version 0.0.43

**Breaking changes**

- `.events.CommandErrorEvent` has been moved from the `errors` module to the `events` module.

**Other changes**

- Added new module, `lightbulb.events`.
- Added two new events, `.events.CommandInvocationEvent` and `.events.CommandCompletionEvent`.
- Added `.commands.Command.before_invoke` and `.commands.Command.after_invoke`.
- Added `.command_handler.when_mentioned_or` to allow you to use the bot's mention as a prefix.
- Added `.context.Context.clean_prefix` to fix wonky looking prefixes due to mentions.
- Fixed help command for single commands having quotes render incorrectly.

## Version 0.0.42

- Changed `user_required_permissions` and `bot_required_permissions` to be `hikari.Permissions` objects.
- Added `.errors.CommandInvocationError` for catching of errors raised during the invocation of a command.
- Fixed greedy args not working with a default.

## Version 0.0.41

- Added support for hikari 2.0.0.dev70.
- Made instance methods work correctly as command specific error handlers.
- Made context accessible through `.events.CommandErrorEvent`.
- Added isort to properly sort the import statements, not that you care.

## Version 0.0.40

- Added the utils `.utils.get` and `.utils.find` helper functions.
- Fix the `__init__.py` for the utils subpackage.

## Version 0.0.39

- Made it so that plugin names with spaces now work in the help command.
- Fixed issue where duplicate commands would appear in help command and in Group.subcommands.
- Added section to `Implementing a Custom Help Command` about using plugins with a custom help command.
- Added a changelog.
