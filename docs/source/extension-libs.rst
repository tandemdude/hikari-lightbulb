.. _extension-libs:

===================
Extension Libraries
===================

This is a collection of libraries that have been written for hikari-lightbulb to aid in the development of your
bots and/or to make your life generally easier during your time with the library.

If you have written an extension library that you would like to have added to this list, please contact thomm.o#8637
on discord.

----

lightbulb-filament
==================

An extension library written by thomm.o which provides various utility methods, extensions, templating, and an alternate
method of declaring commands.

- Repository: `GitHub <https://github.com/tandemdude/filament>`_

- Documentation: `Readthedocs <https://filament.readthedocs.io/en/latest/>`_

Quick Examples
--------------

Declaring commands:

.. code-block:: python

    import lightbulb
    import filament

    class EchoCommand(filament.CommandLike):
        implements = [lightbulb.SlashCommand, lightbulb.PrefixCommand]

        name = "echo"
        description = "repeats the given text"

        text_option = filament.opt("text", "text to repeat")

        async def callback(self, ctx):
            await ctx.respond(ctx.options.text)

For more on what the library provides, you should visit its documentation.

----

lightbulb-neon
==============

An extension library written by NeonJonn which makes it easier to handle and process component interactions using
a class-based menu system.

- Repository: `GitHub <https://github.com/neonjonn/lightbulb-neon>`_

- Documentation: `Readthedocs <https://lightbulb-neon.readthedocs.io/en/latest/>`_

Quick Examples
--------------

Component menu:

.. code-block:: python

    import lightbulb
    import neon

    class Menu(neon.ComponentMenu):
        @neon.button("earth", "earth_button", hikari.ButtonStyle.SUCCESS, emoji="\N{DECIDUOUS TREE}")
        async def earth(self, button: neon.Button) -> None:
            await self.edit_msg(f"{button.emoji} - {button.custom_id}")

        @neon.option("Water", "water", emoji="\N{DROPLET}")
        @neon.option("Fire", "fire", emoji="\N{FIRE}")
        @neon.select_menu("sample_select_menu", "Pick fire or water!")
        async def select_menu_test(self, values: list) -> None:
            await self.edit_msg(f"You chose: {values[0]}!")

        @neon.on_timeout(disable_components=True)
        async def on_timeout(self) -> None:
            await self.edit_msg("\N{ALARM CLOCK} Timed out!")


    @lightbulb.command("neon", "Check out Neon's component builder!")
    @lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
    async def neon_command(ctx: lightbulb.Context) -> None:
        menu = Menu(ctx, timeout=30)
        msg = await ctx.respond("Bar", components=menu.build())
        await menu.run(msg)

----

lightbulb-wtf
=============

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
    from wtf import Command, Options, Option
    from wtf import Implements, Name, Description, Executes

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
