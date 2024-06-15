(v2-changelog)=

# Version 2 Changelog

Below are all the changelogs for the stable versions of hikari-lightbulb (version 2.0.0 to present).

---

## Version 2.3.5

- Fix incorrect parameters being passed to `_get_bucket` which prevented the `add_cooldown` decorator from functioning correctly.

## Version 2.3.4

- Add validators to options in `PrefixContext`
- Fix custom option converter not being initialized for slash commands.
- Implemented slotting in some classes.
- Fixed localization options not being passed to subcommands or command options.
- Added case-insensitive prefixes.
- Add support for Python 3.12.
- Bump hikari requirement to `2.0.0.dev122`.

## Version 2.3.3

- `bucket` attribute has been added to the `lightbulb.errors.MaxConcurrencyLimitReached` class.
- Fix button navigator due to hikari breaking changes.
- Autocomplete callbacks may no longer return instances of `hikari.CommandChoice` as it has been deprecated. Use `AutocompleteChoiceBuilder` instead.

## Version 2.3.2

**Potentially Breaking Changes**

- Module `lightbulb.utils.parser` has been moved up a level to `lightbulb.parser`.
- `OptionsProxy` will now raise an `AttributeError` when trying to access an option that does not exist.

**Other Changes**

- Slash commands now have full custom converter support.
- Permission checks improved to use interaction permission fields where appropriate.
- Fix `lightbulb.commands.base.ApplicationCommand.nsfw` not applying correctly for global commands.
- Implement `min_length` and `max_length` for command options.
- Fix deferral of slash subcommands not working as intended.

## Version 2.3.1

**Potentially Breaking Changes**

- `lightbulb.cooldown_algorithms.CooldownStatus` has been moved from the `buckets` module to the
  `cooldown_algorithms` module.
- `commands_run` attribute has been removed from the `lightbulb.buckets.Bucket` class.

**Other Changes**

- Add `lightbulb.commands.base.CommandLike.nsfw` and `nsfw` kwarg in `lightbulb.decorators.command`
  decorator in order to mark a command as only usable in NSFW channels.
- Deprecate `lightbulb.checks.nsfw_channel_only`. Use the above new feature instead. The check will
  be removed in version `2.4.0`.
- Add `lightbulb.context.base.Context.respond_with_modal`. Note that this will not work if called
  on an instance of `lightbulb.context.prefix.PrefixContext`.
- Add `lightbulb.plugins.Plugin.listeners`.
- Improve `lightbulb.converters.special.MessageConverter` to support conversion of `channelid-messageid` format.
- Implement multiple built-in cooldown algorithms which can be specified when adding a cooldown to a command.

## Version 2.3.0

**Breaking Changes**

- `lightbulb.utils.Parser` api has been completely changed. If you use this class directly
  in your own codebase then you will need to change your code.

**Other Changes**

- Add support for hikari `2.0.0.dev113`.
- Checks should now work in threads.
- Implement application command localization.

## Version 2.2.5

- Add support for Python 3.11.
- Bump hikari requirement to `2.0.0.dev111`.
- Allow a user to iterate through `ctx.options` using {meth}`~lightbulb.context.base.OptionsProxy.items`.

## Version 2.2.4

- Add {meth}`~lightbulb.utils.data_store.DataStore.get_as` to allow `DataStore` to be more type-complete.

## Version 2.2.3

- Implement application command permissions V2. See `lightbulb.decorators.app_command_permissions`.

## Version 2.2.2

- Add ability to edit ephemeral followup responses to application commands.
- Implement `wait_before_execution` for tasks to allow delaying the first task execution.
- `ResponseProxy` is now awaitable to allow you to directly await the response to retreive the message.
- Permission util methods (and by proxy checks) now account for guild owner having all permissions.
- Improve typing and add missing method overloads.
- Improve `CONSUME_REST` to strip leading whitespace before consuming the remaining string.
- Fix subcommand attribute propagation problems when setting initialiser attributes.

## Version 2.2.1

- Add `lightbulb.errors.ConverterFailure.raw_value`.
- Fix context menu commands not able to be registered globally.
- Fix `StartingEvent` listener not correctly being subscribed to in the tasks extension.
- Update `__all__` to add missing items.
- Add `lightbulb.errors.CheckFailure.causes`.
- Fix non-ephemeral followup responses to interactions not being able to be edited.
- Add support for `hikari.Attachment` option type.
- Add kwarg `pass_options` to `lightbulb.decorators.command` decorator.
- Add `lightbulb.decorators.set_max_concurrency`.
- Deprecate `lightbulb.checks.has_attachment`.
- Fix plugins being shown in the default help command even when no commands are visible in the plugin.
- Fix subcommand names being present in `Context.options` for slash subcommands.

## Version 2.2.0

- Fix option serialiser not correctly detecting changes for value for `min|max_value`.
- Add `delete_after` kwarg to `Context.respond`.
- Fix `KeyError` being raised instead of a more appropriate error when attempting to reload an extension that is not already loaded.
- Add `lightbulb.ext.tasks` extension for repeating tasks.
- Fix `ephemeral` and `auto_defer` not working as expected for subcommands.
- Fix subcommands not being registered to more than one command group at a time where it would be expected.
- Add context menu (user and message) commands.
- Fix `BotApp.remove_plugin` not correctly removing plugins from the bot's plugin list.
- Modify the stop emoji for `ButtonNavigator`.
- Add additional validation for slash command options.
- Add `lightbulb.utils.build_invite_url`.
- Rewrite application command management system to reduce the total number of requests made.
- Fix plugins showing in the default help command when there are no commands shown for that plugin.
- Add `__getitem__` implementation for `OptionsProxy`.
- Add `lightbulb.app.BotApp.sync_application_commands`.
- Add support for sending of attachment(s) within interaction initial responses.
- Add typing overloads to `Context.respond`.
- Add `lightbulb.app.BotApp.create_task`.

## Version 2.1.3

- Fix plugin checks not propagating correctly for subcommands.
- Add additional validation to ensure correct decorator order.
- Add `lightbulb.commands.base.OptionLike.min_value` and `lightbulb.commands.base.OptionLike.max_value`.

## Version 2.1.2

- Fix editing ephemeral responses raising a `NotFound` error.
- Fix various type hints.
- Fix `lightbulb.errors.ExtensionNotFound` error being raised when an import fails in an extension being loaded.
- Add `default_enabled_guilds` argument to the `lightbulb.plugins.Plugin` class.

## Version 2.1.1

- Fix error raised when exclusive checks are added to any object.
- Subclasses of `lightbulb.errors.CheckFailure` are no longer wrapped in an additional `lightbulb.errors.CheckFailure`
  object when a check fails.

## Version 2.1.0

- Add `lightbulb.events.LightbulbStartedEvent`.
- Add `cls` kwarg to `lightbulb.decorators.command` and `lightbulb.decorators.option` to allow you to use your
  own `CommandLike` and `OptionLike` classes.
- Add `lightbulb.context.Context.invoked`.
- Implement ability to use namespace packages to extend lightbulb. See `extension-libs`.

## Version 2.0.4

- Fix application command instances being populated only if the command was created.
- Fix application commands only being created for the first given guild ID.
- Fix various typing preventing code written using lightbulb from being mypy compliant.
- Add `__all__` to all init files in order to be able to export more items to top level.

## Version 2.0.3

- Fix `lightbulb.app.BotApp.load_extensions_from` not working on windows computers.
- Fix `lightbulb.checks.has_attachments` not being exported.

## Version 2.0.2

- Allow absolute paths to be passed to `lightbulb.app.BotApp.load_extensions_from`.
- Change `lightbulb.plugins.Plugin.d` and `lightbulb.plugins.Plugin.app` (and `.bot`) to no longer be optional. A
  `RuntimeError` will **always** be raised if the attributes would've returned None.
- Fix various type hints for the `Plugin` and `BotApp` class.
- Fix options with a default value of `0` actually defaulting to `None` instead.

## Version 2.0.1

- Fix slash command groups erroring on creation if using the `@BotApp.command` decorator.
- Add exclusive checks feature. Only one of the exclusive checks will be required to pass in order for the command to be run.
  See the checks API reference page for more information.

## Version 2.0.0

This version is a complete rewrite of the API. Almost everything has been rewritten from scratch so don't expect
much, if any, of the API to be the same as in version 1.

**Changes**

- Lightbulb is now fully typed and mypy compliant.
- Slight memory usage improvements.
- Added ability to do `python -m lightbulb` to give basic version information.
- Rename `lightbulb.Bot` to `lightbulb.BotApp`.
- Complete rewrite of the method used to define commands. See `commands-guide` for details on the new method.
  : - Prefix and slash commands are now defined the same way, and single functions can implement any combination of commands.
    - Options (arguments) are now defined using the `lightbulb.decorators.option` decorator instead of parsing the command signature.
- Plugins are no longer defined as classes. See `plugins-guide` for details on the new method of defining and using plugins.
- Contexts now all have the same interface. `lightbulb.context.base.Context` is the base class.
- Help command has been completely overhauled.
  : - Removed `get_command_signature` function in favour of a `signature` property on command objects.
- Application command management and change detection has been completely overhauled.
- Some errors have been removed, new errors have been added.
- Custom converters have been overhauled to use a base class instead of being functions `lightbulb.converters.base.BaseConverter`.
- Added ability to automatically defer responses to commands, as well as the ability to send all responses from a command
  as ephemeral by default.
- Rewrite permission checks.
- Added many more event types for the additional types of commands available.
- Minor changes to cooldown implementation.
- Added data store module to assist with storing data in the bot (and optionally plugin) instance(s).
- Refactor argument parsing for prefix commands to allow you to drop in your own implementation.
- Minor changes to navigator and paginator implementation - you shouldn't notice these in normal use.
- Command and context classes moved up a level to their respective sub-modules. You can no longer access them with `lightbulb.x`
  you need to instead do `lightbulb.commands|context.x`
- Prefix command groups, subgroups and subcommands now **require** separate classes.
- Added guides section in the documentation.
- Changed documentation theme.
