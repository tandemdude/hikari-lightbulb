.. _plugins-guide:

=======
Plugins
=======

Plugins are structures that allow the grouping of multiple commands and listeners together. They could be considered
synonymous to categories and will show up as such in the default help command.

Plugins can be added to and removed from the bot dynamically. When they are added, all of the commands and listeners
contained within the plugin will be injected into the bot and will be usable.

----

Creating a Plugin
=================

To use plugins, you must first create a ``Plugin`` object and give it a name of your choice:

.. code-block:: python

    import lightbulb

    plugin = lightbulb.Plugin("YourPluginName")

When you instantiate a plugin object, you can also include an option keyword argument ``include_datastore``. When ``True``
this will create an instance of the :obj:`lightbulb.utils.data_store.DataStore` object inside the plugin, accessible through
:obj:`lightbulb.plugins.Plugin.d` that you can use to store any state that you may want. If ``False``, ``Plugin.d`` will be ``None``.

----

Adding Items to Plugins
=======================

The plugin class provides a method :obj:`lightbulb.plugins.Plugin.command` that allows you to register a command to the
plugin object. This method can be used as a first or second order decorator, or called as a function with the command
to add to the plugin.

.. code-block:: python

    import lightbulb

    plugin = lightbulb.Plugin("ExamplePlugin")

    # valid
    @plugin.command
    @lightbulb.command(...)
    @lightbulb.implements(...)
    async def foo(...):
        ...

    # also valid
    @plugin.command()
    @lightbulb.command(...)
    @lightbulb.implements(...)
    async def foo(...):
        ...

    # also valid
    plugin.command(foo)

A similar method is provided to register listeners to the plugin: :obj:`lightbulb.plugins.Plugin.listener`. This method
**cannot** be used as a first order decorator and **must** instead be used as a second order decorator or
called as a function with the listener function to add to the plugin.

This method takes up to 3 arguments depending on how it is called. These are ``event`` (the event type to listen for),
``listener_func`` (this will be populated automatically if using as a decorator and can be ignored, otherwise this is the
function to add to the plugin as a listener) and ``bind`` (this is a keyword argument and defines whether to bind the listener
function to the plugin as a method or not, more on this later).

.. code-block:: python

    import hikari
    import lightbulb

    plugin = lightbulb.Plugin("ExamplePlugin")

    # valid
    @plugin.listener(hikari.Event)
    async def foo(...):
        ...

    # also valid
    plugin.listener(hikari.Event, foo)

----

Plugin Checks
=============

The plugin class supplies a method :obj:`lightbulb.plugins.Plugin.add_checks` which allows you to register checks
to the plugin instead of to commands. All checks added to a plugin will be run for every command defined within that
plugin.

.. code-block:: python

    import lightbulb

    plugin = lightbulb.Plugin("ExamplePlugin")
    plugin.add_checks(lightbulb.owner_only, lightbulb.guild_only, ...)

----

Plugin Error Handling
=====================

You can register a separate error handler function for all the commands within a given plugin using the supplied
:obj:`lightbulb.plugins.Plugin.set_error_handler` method. This method can be used as a second order decorator or called
as a normal function with the function to set the plugin's error handler to. As with the ``listener`` and ``remove_hook``
methods, you can provide a ``bind`` kwarg to define whether or not the function should be bound to the plugin.

.. code-block:: python

    import lightbulb

    plugin = lightbulb.Plugin("ExamplePlugin")

    # valid
    @plugin.set_error_handler()
    async def foo(...):
        ...

    # also valid
    plugin.set_error_handler(foo)

----

Plugin Remove Hook
==================

You can register a hook function that will be run when the plugin is removed from the bot using the provided
:obj:`lightbulb.plugins.Plugin.remove_hook` method. This can be used as a second order decorator or called as a function
with the function to set the plugin's remove hook to. This method also allows you to provide the ``bind`` kwarg to specify
whether or not to bind the function to the plugin or not.

.. code-block:: python

    import lightbulb

    plugin = lightbulb.Plugin("ExamplePlugin")

    # valid
    @plugin.remove_hook()
    async def foo(...):
        ...

    # also valid
    plugin.remove_hook(foo)

----

Binding Functions to Plugins
============================

Some plugin methods allow you to bind a function to the plugin. This will call ``__get__`` on the function you provide the
method with before setting the appropriate plugin attribute. This will transform the function into a bound method, meaning
it will be called with an additional argument (the equivalent of ``self``, except outside of a class) which, when called
will be the instance of the plugin that the function was bound to.

.. code-block:: python

    import hikari
    import lightbulb

    plugin = lightbulb.Plugin("ExamplePlugin")

    # signature for unbound listener function
    @plugin.listener(hikari.Event)
    async def some_listener(event: hikari.Event) -> None:
        # this function is unbound, so will **only** be called with
        # the event instance that it was listening for
        ...

    # signature for bound listener function
    @plugin.listener(hikari.Event, bind=True)
    async def some_listener(plugin: lightbulb.Plugin, event: hikari.Event) -> None
        # this function is **bound** so will be called with the plugin instance that it
        # was bound to when the event it is listening for is dispatched
        ...
