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

lightbulb-ext-tungsten
======================

An extension library written by Christian-Tarello(Villager#5118) which provides an easier structure for building, editing and running
button groups and select menus. 

- Repository: `GitHub <https://github.com/Christian-Tarello/lightbulb-ext-tungsten>`_

- Documentation: `Readthedocs <https://lightbulb-tungsten.readthedocs.io/en/latest/>`_

Quick Examples
--------------

Making and running a button group:

.. code-block:: python

    import hikari

    import lightbulb
    from lightbulb.ext.tungsten import tungsten

    class ExampleButtons(tungsten.Components):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.button_group = self.create_button_group()
            
            
        def create_button_group(self):
            button_states = {
                    0: tungsten.ButtonState(label = "RED", style=hikari.ButtonStyle.DANGER, emoji="💣"),
                    1: tungsten.ButtonState(label="GREY", style=hikari.ButtonStyle.SECONDARY),
                    2: tungsten.ButtonState(label="GREEN", style=hikari.ButtonStyle.SUCCESS, emoji="👍"),
                    3: tungsten.ButtonState(label="BLURPLE", style=hikari.ButtonStyle.PRIMARY)
                }
            button_rows = [
                    [
                    tungsten.Button(state=0, button_states=button_states),
                    tungsten.Button(state=1, button_states=button_states),
                    tungsten.Button(state=2, button_states=button_states),
                    tungsten.Button(state=3, button_states=button_states),
                    ]
                ]
            return tungsten.ButtonGroup(button_rows)
        
        async def button_callback(
            self, 
            button: tungsten.Button, 
            x: int, 
            y: int, 
            interaction: hikari.ComponentInteraction
            ) -> None:
            state_cycle = {
                0:1,
                1:2,
                2:3,
                3:0,
            }
            self.button_group.edit_button(x, y, state = state_cycle[button.state])
            await self.edit_msg(f"{button.style.name}", components = self.build())

    @bot.command
    @lightbulb.command("tungsten", "Test the tungsten extension library.")
    @lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
    async def tungsten_example_comand(ctx: lightbulb.Context) -> None:
        buttons = ExampleButtons(ctx)
        resp = await ctx.respond(f"Tungsten", components = buttons.build())
        await buttons.run(resp)
----

More coming soon (hopefully).
