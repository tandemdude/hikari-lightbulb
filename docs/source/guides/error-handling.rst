==============
Error Handling
==============

Errors are a thing you will undoubtebly encounter during your bot development journey - this is unavoidable. In addition
to you maybe writing code that doesn't do what you expected it to do, lightbulb will raise errors on its own depending
on the situation. For example, lightbulb will raise errors when command checks or converters fail - now this is not
your fault, it is the fault of the user for running your command incorrectly!

Now naturally, it is not ideal for your bot to just not respond to command invocations if something goes wrong. It would
be much better for the bot to display a message telling the user what they did/went wrong to allow them to fix it
for next time. This is what error handling is for!

Lightbulb (through hikari) allows you to have global error handlers (listeners) if you want all of your error messages
to look the same no matter the command that was run. It is also possible to have command-specific and plugin-specific
error handlers.

----

Resolution Order
================

When handling errors, lightbulb will try to find and then call error handlers in this order:

- Command-specific error handler (see :obj:`lightbulb.commands.base.CommandLike.set_error_handler`)

- Plugin-specific error handler (see :obj:`lightbulb.plugins.Plugin.set_error_handler`)

- Global error handler

- Raises error if not handled

Command-specific and plugin-specific error handlers are a special case. They should return a boolean indicating whether
or not the error could be handled by that handler. If ``False`` is returned, then the error will propogate down the list
to the next applicable error handler.

For global error handlers, a return value cannot be retrieved and so if you cannot handle the error in the handler then
you should have a ``raise`` statement at the bottom of the handler function.

----

Creating a Global Error Handler
===============================

Global error handlers are just listeners for the lightbulb error event (:obj:`lightbulb.events.CommandErrorEvent`) and
so are defined exactly the same way that you'd create a listener for any other event.

.. code-block:: python

    import lightbulb

    bot = lightbulb.BotApp(...)

    @bot.listen(lightbulb.CommandErrorEvent)
    async def on_error(event: lightbulb.CommandErrorEvent) -> None:
        ...

The :obj:`lightbulb.events.CommandErrorEvent` contains an ``exception`` attribute which stores the instance of the
exception that caused the event to be dispatched. This attribute will **always** be an instance of a subclass of
:obj:`lightbulb.errors.LightbulbError`.

.. important::
    Lightbulb wraps some exceptions that get raised in its own exception classes internally to allow them to be dealt
    with more easily. When this is the case (e.g. for ``CheckFailure`` and ``CommandInvocationError``) you can access
    the original exception using ``exception.__cause__``.

----

Example Error Handler
=====================

.. code-block:: python

    import lightbulb

    bot = lightbulb.BotApp(...)

    @bot.listen(lightbulb.CommandErrorEvent)
    async def on_error(event: lightbulb.CommandErrorEvent) -> None:
        if isinstance(event.exception, lightbulb.CommandInvocationError):
            await event.context.respond(f"Something went wrong during invocation of command `{event.context.command.name}`.")
            raise event.exception

        # Unwrap the exception to get the original cause
        exception = event.exception.__cause__ or event.exception

        if isinstance(exception, lightbulb.NotOwner):
            await event.context.respond("You are not the owner of this bot.")
        elif isinstance(exception, lightbulb.CommandIsOnCooldown):
            await event.context.respond(f"This command is on cooldown. Retry in `{exception.retry_after:.2f}` seconds.")
        elif ...:
            ...
        else:
            raise exception
