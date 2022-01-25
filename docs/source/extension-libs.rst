.. _extension-libs:

===================
Extension Libraries
===================

--------
Built In
--------

These extension libraries are included with hikari-lightbulb. You do not need to install any
additional dependencies to make use of these.

lightbulb.ext.tasks
===================

.. automodule:: lightbulb.ext.tasks
    :members:
    :member-order: bysource

----

-----------
Third Party
-----------

This is a collection of libraries that have been written for hikari-lightbulb to aid in the development of your
bots and/or to make your life generally easier during your time with the library.

If you have written an extension library that you would like to have added to this list, please contact ``thomm.o#8637``
on discord.

----

lightbulb-ext-filament
======================

An extension library written by thomm.o which provides various utility methods, extensions, templating, and an alternate
method of declaring commands.

- Repository: `GitHub <https://github.com/tandemdude/lightbulb-ext-filament>`_

- Documentation: `Readthedocs <https://filament.readthedocs.io/en/latest/>`_

Quick Examples
--------------

Declaring commands:

.. code-block:: python

    import lightbulb
    from lightbulb.ext import filament

    class EchoCommand(filament.CommandLike):
        implements = [lightbulb.SlashCommand, lightbulb.PrefixCommand]

        name = "echo"
        description = "repeats the given text"

        text_option = filament.opt("text", "text to repeat")

        async def callback(self, ctx):
            await ctx.respond(ctx.options.text)

For more on what the library provides, you should visit its documentation.

----

lightbulb-ext-wtf
=================

A library written by thomm.o which provides a completely different method of declaring commands. This library started
out as a joke to see how badly python's syntax could be abused but turned in to a fully functional method of declaring
lightbulb commands.

- Repository: `GitHub <https://github.com/tandemdude/lightbulb-wtf>`_

- Documentation: `Readthedocs <https://lightbulb-wtf.readthedocs.io/en/latest/>`_

Quick Examples
--------------

Declaring commands:

.. code-block:: python

    import lightbulb
    from lightbulb.ext.wtf import Command, Options, Option
    from lightbulb.ext.wtf import Implements, Name, Description, Executes

    echo = Command[
        Implements[lightbulb.SlashCommand, lightbulb.PrefixCommand],
        Name["echo"],
        Description["repeats the given text"],
        Options[
            Option[
                Name["text"],
                Description["text to repeat"],
            ],
        ],
        Executes[lambda ctx: ctx.respond(ctx.options.text)],
    ]

----

More coming soon (hopefully).
