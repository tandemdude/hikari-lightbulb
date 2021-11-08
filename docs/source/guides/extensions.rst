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
    The `example extension <https://github.com/tandemdude/hikari-lightbulb/blob/development/examples/extension_example.py>`_

----

Loading Extensions
==================

After you have created an extension, you need to load it into the bot so that all the commands and/or plugins get
registered. The :obj:`lightbulb.app.BotApp` class provides three relevant methods to help with this:

- :obj:`lightbulb.app.BotApp.load_extensions`

- :obj:`lightbulb.app.BotApp.load_extensions_from`

- :obj:`lightbulb.app.BotApp.unload_extensions`

- :obj:`lightbulb.app.BotApp.reload_extensions`

In the example below we will be making use of :obj:`lightbulb.app.BotApp.load_extensions`.

Example file structure:

.. code-block::

    example_project/
    ├─ extensions/
    │  ├─ __init__.py
    │  ├─ extension.py
    ├─ bot.py

To load the extension ``extension.py`` from the main ``bot.py`` file, you would call ``BotApp.load_extensions`` with the
argument ``"extensions.extension"`` (the import path for that module).

An example ``bot.py`` file can be seen below:

.. code-block:: python

    import lightbulb

    bot = lightbulb.BotApp(...)

    bot.load_extensions("extensions.extension")

    bot.run()
