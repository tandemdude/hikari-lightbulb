==========
Extensions
==========

Extensions are a method of separating your bot's code into multiple files, which can be loaded and unloaded from the
bot at any time. Extensions are hot-reloadable which means that they can be reloaded even while the bot is running.

Extension reloading using ``BotApp.reload_extensions`` is atomic, meaning that if any stage of the unload or load
fails, then the code will be reverted to the last working state.

----

Creating an Extension
=====================

All extension files must include a function ``load`` in order for the bot to recognise it as an extension. You should
use the load function to add any commands or plugins to the bot that are present in that extension.

If you want to be able to unload and reload extensions, you must also include a function ``unload`` which will be called
and should remove any commands or plugins from the bot that are present in the extension.

Both the ``load`` and ``unload`` functions should take a single argument, which will be the ``BotApp`` instance
that the extension is being loaded into.

**Example extension:**

.. code-block:: python

    import lightbulb

    plugin = lightbulb.Plugin("ExamplePlugin")

    @plugin.command
    @lightbulb.command(...)
    @lightbulb.implements(...)
    async def foo(ctx):
        ...


    def load(bot):
        bot.add_plugin(plugin)

    def unload(bot):
        bot.remove_plugin(plugin)


.. seealso::
    The `example extension <https://github.com/tandemdude/hikari-lightbulb/blob/v2/examples/extension_example.py>`_
