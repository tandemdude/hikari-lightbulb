.. _checks:

====================
Checks API Reference
====================

.. automodule:: lightbulb.checks
   :members:

----

Exclusive Checks
================

Check objects support the bitwise or (``|``) operator for the creation of exclusive checks. This allows you to add
a check to the command which will pass if any one of the provided checks pass instead of requiring all of the checks
to pass.

To create an exclusive check, use the bitwise or operator on two or more check objects:

.. code-block:: python

    import lightbulb

    @lightbulb.add_checks(lightbulb.guild_only | lightbulb.owner_only)
    @lightbulb.command(...)
    @lightbulb.implements(...)
    async def foo(...):
        ...

The above command is restricted to being used **only** in guilds, unless the invoker of the command is also the owner
of the bot, in which case the owner would be allowed to use the command in DMs.
