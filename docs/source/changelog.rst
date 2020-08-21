=========
Changelog
=========

Here you will find the changelogs for most if not every lightbulb update since version **0.0.38**.

If you think anything is missing, make a merge request to add it, or contact thomm.o on discord.

----

Version 0.0.42
==============

- Changed ``user_required_permissions`` and ``bot_required_permissions`` to be :obj:`hikari.Permissions` objects.

- Added :obj:`~.errors.CommandInvocationError` for catching of errors raised during the invocation of a command.

- Fixed greedy args not working with a default.

Version 0.0.41
==============

- Added support for hikari 2.0.0.dev70.

- Made instance methods work correctly as command specific error handlers.

- Made context accessible through :obj:`~.errors.CommandErrorEvent`.

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
