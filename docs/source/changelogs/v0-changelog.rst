=====================
Pre-Release Changelog
=====================

Below are all the changelogs for the pre-release versions of hikari-lightbulb (version 0.0.38 to 0.0.61).

----


Version 0.0.61
==============

**Breaking Changes**

- Removed ``ArgInfo`` dataclass.

- Rewritten :obj:`~lightbulb.commands.SignatureInspector` class.

- :obj:`~lightbulb.command_handler.Bot.resolve_args_for_command` now takes an additional argument ``context``.

- Calling :obj:`~lightbulb.commands.Command.invoke` will no longer process converters.

- Changed :obj:`~lightbulb.cooldowns.CooldownManager.add_cooldown` into a coroutine.

**Other Changes**

- Added :obj:`~lightbulb.checks.has_attachment`.

- Added :obj:`~lightbulb.checks.check_exempt`.

- Fixed :obj:`KeyError` being raised when attempting to remove a command/plugin that doesn't exist

- Created class mapping for converters. See :ref:`converters` for details.

- Added support for custom cooldowns through the :obj:`~lightbulb.cooldowns.dynamic_cooldown` decorator.

- Added :obj:`lightbulb.converters.Greedy` converter.

Version 0.0.60
==============

- Added :obj:`~lightbulb.events.LightbulbEvent.bot` property.

- Fixed admin permission checks not working as expected.

Version 0.0.59
==============

**Breaking Changes**

- :obj:`~lightbulb.plugins.Plugin.commands` changed to a :obj:`set` from a :obj:`dict` for consistency.

**Other Changes**

- Added :obj:`~lightbulb.plugins.Plugin.walk_commands`.

Version 0.0.58
==============

**Breaking Changes**

- :obj:`~lightbulb.context.Context.reply` renamed to :obj:`~lightbulb.context.Context.respond` for consistency with hikari.

**Other Changes**

- Fix :obj:`IndexError` raised when no command provided after the prefix.

- Fix :obj:`~lightbulb.checks.human_only` and add :obj:`~lightbulb.checks.webhook_only`.

- Fix :obj:`~lightbulb.converters.role_converter` incorrectly converting from mentions.

- Include support for hikari `2.0.0.dev98`.

Version 0.0.57
==============

- Add `missing_args` parameter to :obj:`~lightbulb.errors.NotEnoughArguments`.

- Fix `__iter__` for :obj:`~lightbulb.converters.WrappedArg`.

- Improve :obj:`~lightbulb.command_handler.Bot.get_command` to allow you to get subcommands without having to call :obj:`~lightbulb.commands.Group.get_subcommand`.

Version 0.0.56
==============

- Move docs to [readthedocs](https://hikari-lightbulb.readthedocs.io/en/latest/).

- Refactor errors to ensure they get instantiated correctly everywhere they are used.

- Fix various check messages and an issue where a check decorator added an incorrect check function.

Version 0.0.55
==============

- Fix issue with errors not being raised correctly.

- Fix :obj:`~lightbulb.help.get_command_signature` showing ctx for subcommands.

- Make :obj:`~lightbulb.checks.bot_has_guild_permissions` and :obj:`~lightbulb.checks.has_guild_permissions` pass if bot or invoker has the administrator permission.

Version 0.0.54
==============

- Various performance improvements.

Version 0.0.53
==============

- Fix print_banner.

- Bump requirements.

Version 0.0.52
==============

**Breaking changes**

- Removed custom_emoji_converter and replaced it with :obj:`~.converters.emoji_converter`.

**Other changes**

- Added :obj:`~.checks.has_permissions` and :obj:`~.checks.bot_has_permissions`.

- Added :obj:`~.converters.guild_converter`.

- Exposed navigator callbacks to make it easier to supply your own buttons.

- Fixed navigator not working with custom emojis when using your own buttons.

Version 0.0.51
==============

- Added support for hikari 2.0.0.dev85.

Version 0.0.50
==============

- Fixed :obj:`~.context.channel`.

- Added NSFW channel only check.

- Ensured all docstrings are correct and up to date, including any examples.

Version 0.0.49
==============

- Improved help docstring format parsing.

- Fixed :obj:`~.help.get_command_signature` no longer working due to an :obj:`AttributeError`.

- Fixed :obj:`~.command_handler.Bot.send_help` no longer working.

Version 0.0.48
==============

- Added :obj:`~.converters.colour_converter` and :obj:`~.converters.message_converter`.

- Added support for :obj:`typing.Union` and :obj:`typing.Optional` as converters/typehints.

- Exposed the current help class the bot uses through :attr:`~.command_handler.Bot.help_command`.

- Added support for a custom cooldown manager class through the :obj:`~.cooldowns.cooldown` decorator.

- Improved the error message for :obj:`~.errors.CommandInvocationError`.

Version 0.0.47
==============

- Added :obj:`~.context.Context.channel` and :obj:`~.context.Context.guild` properties.

- Added :obj:`~.plugins.Plugin.plugin_check` method.

- Added :obj:`~.converters.custom_emoji_converter`.

- Made converters work when the arg is a name/name#discrim/nickname/etc

- Added support for hikari 2.0.0.dev75

Version 0.0.46
==============

- Fixed converters not working with kwargs for commands in plugins.

- Improved README.md.

- Added documentation and public method for how to customise how arguments are parsed.

Version 0.0.45
==============

- Rewrote the argument parsing system and greedy arg system.

- Made converters work for greedy args.

- Added functionality to :obj:`~.stringview.StringView` to allow it to only parse up to a specified number of args.

- Abstracted the :obj:`~.command_handler.Bot.handle` method to make it easier to override to customise functionality.

Version 0.0.44
==============

- Improved :obj:`~.command_handler.Bot.walk_commands`.

- Added :obj:`~.commands.Group.walk_commands`.

- Added :obj:`~.commands.Command.qualified_name`, :obj:`~.commands.Command.callback`, :obj:`~.commands.Command.checks`.

- Fixed wonky default help for command groups.

- Added :obj:`~.context.Context.send_help` and :obj:`~.command_handler.Bot.send_help`.

- Added :obj:`~.command_handler.Bot.get_context`.

- Added :obj:`~.command_handler.Bot.help_class`.

Version 0.0.43
==============

**Breaking changes**

- :obj:`~.events.CommandErrorEvent` has been moved from the ``errors`` module to the ``events`` module.

**Other changes**

- Added new module, ``lightbulb.events``.

- Added two new events, :obj:`~.events.CommandInvocationEvent` and :obj:`~.events.CommandCompletionEvent`.

- Added :obj:`~.commands.Command.before_invoke` and :obj:`~.commands.Command.after_invoke`.

- Added :obj:`~.command_handler.when_mentioned_or` to allow you to use the bot's mention as a prefix.

- Added :obj:`~.context.Context.clean_prefix` to fix wonky looking prefixes due to mentions.

- Fixed help command for single commands having quotes render incorrectly.

Version 0.0.42
==============

- Changed ``user_required_permissions`` and ``bot_required_permissions`` to be :obj:`hikari.Permissions` objects.

- Added :obj:`~.errors.CommandInvocationError` for catching of errors raised during the invocation of a command.

- Fixed greedy args not working with a default.

Version 0.0.41
==============

- Added support for hikari 2.0.0.dev70.

- Made instance methods work correctly as command specific error handlers.

- Made context accessible through :obj:`~.events.CommandErrorEvent`.

- Added isort to properly sort the import statements, not that you care.

Version 0.0.40
==============

- Added the utils :obj:`~.utils.get` and :obj:`~.utils.find` helper functions.

- Fix the ``__init__.py`` for the utils subpackage.

Version 0.0.39
==============

- Made it so that plugin names with spaces now work in the help command.

- Fixed issue where duplicate commands would appear in help command and in Group.subcommands.

- Added section to :ref:`Implementing a Custom Help Command <custom-help>` about using plugins with a custom help command.

- Added a changelog.
