===================
Version 2 Changelog
===================

Below are all the changelogs for the stable versions of hikari-lightbulb (version 2.0.0 to present).

----

Version 2.2.5
=============

- Add support for Python 3.11.

- Bump hikari requirement to ``2.0.0.dev111``.

- Allow a user to iterate through ``ctx.options`` using :meth:`~lightbulb.context.base.OptionsProxy.items`.

Version 2.2.4
=============

- Add :meth:`~lightbulb.utils.data_store.DataStore.get_as` to allow ``DataStore`` to be more type-complete.

Version 2.2.3
=============

- Implement application command permissions V2. See :obj:`~lightbulb.decorators.app_command_permissions`.

Version 2.2.2
=============

- Add ability to edit ephemeral followup responses to application commands.

- Implement ``wait_before_execution`` for tasks to allow delaying the first task execution.

- ``ResponseProxy`` is now awaitable to allow you to directly await the response to retreive the message.

- Permission util methods (and by proxy checks) now account for guild owner having all permissions.

- Improve typing and add missing method overloads.

- Improve ``CONSUME_REST`` to strip leading whitespace before consuming the remaining string.

- Fix subcommand attribute propagation problems when setting initialiser attributes.

Version 2.2.1
=============

- Add :obj:`lightbulb.errors.ConverterFailure.raw_value`.

- Fix context menu commands not able to be registered globally.

- Fix ``StartingEvent`` listener not correctly being subscribed to in the tasks extension.

- Update ``__all__`` to add missing items.

- Add :obj:`lightbulb.errors.CheckFailure.causes`.

- Fix non-ephemeral followup responses to interactions not being able to be edited.

- Add support for ``hikari.Attachment`` option type.

- Add kwarg ``pass_options`` to :obj:`lightbulb.decorators.command` decorator.

- Add :obj:`lightbulb.decorators.set_max_concurrency`.

- Deprecate :obj:`lightbulb.checks.has_attachment`.

- Fix plugins being shown in the default help command even when no commands are visible in the plugin.

- Fix subcommand names being present in ``Context.options`` for slash subcommands.

Version 2.2.0
=============

- Fix option serialiser not correctly detecting changes for value for ``min|max_value``.

- Add ``delete_after`` kwarg to ``Context.respond``.

- Fix ``KeyError`` being raised instead of a more appropriate error when attempting to reload an extension that is not already loaded.

- Add ``lightbulb.ext.tasks`` extension for repeating tasks.

- Fix ``ephemeral`` and ``auto_defer`` not working as expected for subcommands.

- Fix subcommands not being registered to more than one command group at a time where it would be expected.

- Add context menu (user and message) commands.

- Fix ``BotApp.remove_plugin`` not correctly removing plugins from the bot's plugin list.

- Modify the stop emoji for ``ButtonNavigator``.

- Add additional validation for slash command options.

- Add :obj:`lightbulb.utils.build_invite_url`.

- Rewrite application command management system to reduce the total number of requests made.

- Fix plugins showing in the default help command when there are no commands shown for that plugin.

- Add ``__getitem__`` implementation for ``OptionsProxy``.

- Add :obj:`lightbulb.app.BotApp.sync_application_commands`.

- Add support for sending of attachment(s) within interaction initial responses.

- Add typing overloads to ``Context.respond``.

- Add :obj:`lightbulb.app.BotApp.create_task`.

Version 2.1.3
=============

- Fix plugin checks not propagating correctly for subcommands.

- Add additional validation to ensure correct decorator order.

- Add :obj:`lightbulb.commands.base.OptionLike.min_value` and :obj:`lightbulb.commands.base.OptionLike.max_value`.

Version 2.1.2
=============

- Fix editing ephemeral responses raising a ``NotFound`` error.

- Fix various type hints.

- Fix :obj:`lightbulb.errors.ExtensionNotFound` error being raised when an import fails in an extension being loaded.

- Add ``default_enabled_guilds`` argument to the :obj:`lightbulb.plugins.Plugin` class.

Version 2.1.1
=============

- Fix error raised when exclusive checks are added to any object.

- Subclasses of :obj:`lightbulb.errors.CheckFailure` are no longer wrapped in an additional :obj:`lightbulb.errors.CheckFailure`
  object when a check fails.

Version 2.1.0
=============

- Add :obj:`lightbulb.events.LightbulbStartedEvent`.

- Add ``cls`` kwarg to :obj:`lightbulb.decorators.command` and :obj:`lightbulb.decorators.option` to allow you to use your
  own ``CommandLike`` and ``OptionLike`` classes.

- Add :obj:`lightbulb.context.Context.invoked`.

- Implement ability to use namespace packages to extend lightbulb. See :ref:`extension-libs`.

Version 2.0.4
=============

- Fix application command instances being populated only if the command was created.

- Fix application commands only being created for the first given guild ID.

- Fix various typing preventing code written using lightbulb from being mypy compliant.

- Add ``__all__`` to all init files in order to be able to export more items to top level.

Version 2.0.3
=============

- Fix :obj:`lightbulb.app.BotApp.load_extensions_from` not working on windows computers.

- Fix :obj:`lightbulb.checks.has_attachments` not being exported.

Version 2.0.2
=============

- Allow absolute paths to be passed to :obj:`lightbulb.app.BotApp.load_extensions_from`.

- Change :obj:`lightbulb.plugins.Plugin.d` and :obj:`lightbulb.plugins.Plugin.app` (and ``.bot``) to no longer be optional. A
  :obj:`RuntimeError` will **always** be raised if the attributes would've returned None.

- Fix various type hints for the ``Plugin`` and ``BotApp`` class.

- Fix options with a default value of ``0`` actually defaulting to ``None`` instead.

Version 2.0.1
=============

- Fix slash command groups erroring on creation if using the ``@BotApp.command`` decorator.

- Add exclusive checks feature. Only one of the exclusive checks will be required to pass in order for the command to be run.
  See the checks API reference page for more information.

Version 2.0.0
=============

This version is a complete rewrite of the API. Almost everything has been rewritten from scratch so don't expect
much, if any, of the API to be the same as in version 1.

**Changes**

- Lightbulb is now fully typed and mypy compliant.

- Slight memory usage improvements.

- Added ability to do ``python -m lightbulb`` to give basic version information.

- Rename ``lightbulb.Bot`` to ``lightbulb.BotApp``.

- Complete rewrite of the method used to define commands. See :ref:`commands-guide` for details on the new method.
    - Prefix and slash commands are now defined the same way, and single functions can implement any combination of commands.

    - Options (arguments) are now defined using the :obj:`lightbulb.decorators.option` decorator instead of parsing the command signature.

- Plugins are no longer defined as classes. See :ref:`plugins-guide` for details on the new method of defining and using plugins.

- Contexts now all have the same interface. :obj:`lightbulb.context.base.Context` is the base class.

- Help command has been completely overhauled.
    - Removed ``get_command_signature`` function in favour of a ``signature`` property on command objects.

- Application command management and change detection has been completely overhauled.

- Some errors have been removed, new errors have been added.

- Custom converters have been overhauled to use a base class instead of being functions :obj:`lightbulb.converters.base.BaseConverter`.

- Added ability to automatically defer responses to commands, as well as the ability to send all responses from a command
  as ephemeral by default.

- Rewrite permission checks.

- Added many more event types for the additional types of commands available.

- Minor changes to cooldown implementation.

- Added data store module to assist with storing data in the bot (and optionally plugin) instance(s).

- Refactor argument parsing for prefix commands to allow you to drop in your own implementation.

- Minor changes to navigator and paginator implementation - you shouldn't notice these in normal use.

- Command and context classes moved up a level to their respective sub-modules. You can no longer access them with ``lightbulb.x``
  you need to instead do ``lightbulb.commands|context.x``

- Prefix command groups, subgroups and subcommands now **require** separate classes.

- Added guides section in the documentation.

- Changed documentation theme.
