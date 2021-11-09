===================
Version 2 Changelog
===================

Below are all the changelogs for the stable versions of hikari-lightbulb (version 2.0.0 to present).

----

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

See below for the (mostly) completed rewrite todo:

.. code-block:: markdown

    - [x] Custom Bot Class
      - [x] Bot Checks
      - [x] Multiple Owners
      - [x] Get prefix function (sync or async)

    - [x] Plugins
      - [x] Support Prefix Commands
      - [x] Support Slash Commands
      - [x] Support Message Commands
      - [x] Support User Commands
      - [x] Support Listeners
      - [x] Plugin Unload Hook
      - [x] Plugin Check
      - [x] Plugin error handler

    - [x] Extensions
      - [x] Load
      - [x] Unload
      - [x] Reload

    - [ ] Commands
      - [x] Base Command
      - [x] Base Application Command (needs creation methods)
      - [x] Prefix Commands
        - [x] Invocation
        - [x] Parsing
        - [x] Groups & subcommands
      - [ ] Slash Commands
        - [x] Option Types
        - [x] Channel Types
        - [x] Groups & subcommands
        - [ ] ~~Autocomplete~~ (blocked)
      - [ ] ~~Message Commands~~ (blocked)
      - [ ] ~~User Commands~~ (blocked)
      - [x] Per-Command Error Handler
        - [x] Prefix commands
        - [x] Slash commands
        - [x] ~~Message commands~~ (blocked)
        - [x] ~~User commands~~ (blocked)
      - [ ] Auto-managing of Application Commands
        - [x] Slash Commands
        - [ ] ~~Message commands~~ (blocked)
        - [ ] ~~User commands~~ (blocked)

    - [x] Checks (Reuse?)
      - [x] DM Only
      - [x] Guild Only
      - [x] Human Only
      - [x] Bot Only
      - [x] Webhook Only
      - [x] Owner Only
      - [x] Has Roles
      - [x] (Bot) Has Guild Permissions
      - [x] (Bot) Has Role Permissions
      - [x] (Bot) Has Channel Permissions
      - [x] Has Attachment
      - [x] Custom Checks
      - [x] Check Exempt?

    - [ ] Context
      - [x] Base Class
      - [x] Prefix Context
      - [x] Slash Context
      - [ ] ~~Message Context~~ (blocked)
      - [ ] ~~User Context~~ (blocked)

    - [x] Converters
      - [x] Base Converter
      - [x] User Converter
      - [x] Member Converter
      - [x] Guild Channel Converter
      - [x] Guild Voice Channel Converter
      - [x] Category Converter
      - [x] Guild Text Channel Converter
      - [x] Role Converter
      - [x] Emoji Converter
      - [x] Guild Converter
      - [x] Message Converter
      - [x] Invite Converter
      - [x] Colo(u)r Converter
      - [x] Timestamp Converter

    - [ ] Special Converter Support for Slash Commands?

    - [x] Special Args
      - [x] Greedy
      - [x] Consume Rest

    - [x] Cooldowns (Reuse?)

    - [x] Events
      - [x] *Command Completion Event
      - [x] *Command Invocation Event
      - [x] *Command Error Event

    - [x] Errors (Reuse?)

    - [ ] Parsing
      - [x] Standard Parser
      - [ ] CLI Parser
      - [x] Custom Parsing

    - [x] Help Command

    - [x] Paginators (Reuse?)

    - [x] Navigators (Reuse?)

    - [x] Utils (Reuse?)
      - [x] get
      - [x] find
      - [x] permissions_in
      - [x] permissions_for

    - [ ] Command validation
      - [x] Prefix commands
      - [x] Slash commands
      - [ ] Message commands
      - [ ] User commands

    - [x] Paginated/Navigated Help Command
    - [ ] Embed Help Command
    - [x] Default Ephemeral Flags
    - [ ] Reinvoke on edits
    - [x] Broadcast typing on command invocation
    - [x] Default enabled guilds
    - [x] Automatically defer responses
