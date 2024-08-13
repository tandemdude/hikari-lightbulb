# -*- coding: utf-8 -*-
# Copyright (c) 2023-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
This package contains a framework for creating your own component and modal handlers, without having to go
through the common issues when trying to do it using raw Hikari.

----

Component Handling
------------------

Creating a Menu
^^^^^^^^^^^^^^^

Creating your own component handler is as easy as creating a subclass of the :obj:`~lightbulb.components.menus.Menu`
class.

.. dropdown:: Example

    Creating a menu.

    .. code-block:: python

        import lightbulb

        class MyMenu(lightbulb.components.Menu):
            def __init__(self) -> None:
                ...

A single menu class encapsulates the components and state that will be used when handling interactions for any
of the attached components.

Adding Components to Menus
^^^^^^^^^^^^^^^^^^^^^^^^^^

You can add components to a menu using any of the appropriate methods:

- :meth:`~lightbulb.components.menus.Menu.add_interactive_button`
- :meth:`~lightbulb.components.menus.Menu.add_link_button`
- :meth:`~lightbulb.components.menus.Menu.add_text_select`
- :meth:`~lightbulb.components.menus.Menu.add_user_select`
- :meth:`~lightbulb.components.menus.Menu.add_role_select`
- :meth:`~lightbulb.components.menus.Menu.add_mentionable_select`
- :meth:`~lightbulb.components.menus.Menu.add_channel_select`

The menu will lay out the added components into rows automatically. If you wish to customise the layout, you
can use the methods :meth:`~lightbulb.components.base.BuildableComponentContainer.next_row` and
:meth:`~lightbulb.components.base.BuildableComponentContainer.previous_row` to move between rows while adding
components. If a row becomes full (either through having five buttons, or one select), then the menu will
**always** move to the next row if you add another component to it.

When adding a component to a menu, the methods return an object representing the created component. It is recommended
that you store this component within an instance variable so that you can modify it later if you wish to update
the menu's appearance.

.. dropdown:: Example

    Adding a component to a menu.

    .. code-block:: python

        import lightbulb

        class MyMenu(lightbulb.components.Menu):
            def __init__(self) -> None:
                self.btn = self.add_interactive_button(
                    hikari.ButtonStyle.PRIMARY,
                    self.on_button_press,
                    label="Test Button",
                )

            async def on_button_press(self, ctx: lightbulb.components.MenuContext) -> None:
                await ctx.respond("Button pressed!")

Running Menus
^^^^^^^^^^^^^

To send a menu with a message, you can pass the menu instance to the ``components`` argument of the method you
are using (i.e. ``Context.respond``, ``RESTClient.create_message``) - it will be automatically built and sent
with the message.

Menus require the Lightbulb :obj:`~lightbulb.client.Client` in order to listen for the appropriate interactions. You
can run a menu by calling the :meth:`~lightbulb.components.menus.Menu.attach` method. When calling this method,
you can optionally choose to wait until the menu completes before continuing, and pass a timeout after which
time an :obj:`asyncio.TimeoutError` will be raised.

If you do not pass ``wait=True`` to the ``attach()`` method, then it is recommended that you pass your own known
custom IDs when you are adding components to the menu - otherwise they will be randomly generated and the menu will
probably not work as you intended.

To get your ``Client`` instance within a command, you can use dependency injection as seen in the following example.
Check the "Dependencies" guide within the by-example section of the documentation for more details about dependency
injection.

.. dropdown:: Example

    Attaching the menu to a client instance within a command.

    .. code-block:: python

        import lightbulb

        class MyMenu(lightbulb.components.Menu):
            def __init__(self) -> None:
                self.btn = self.add_interactive_button(
                    hikari.ButtonStyle.PRIMARY,
                    self.on_button_press,
                    label="Test Button",
                )

            async def on_button_press(self, ctx: lightbulb.components.MenuContext) -> None:
                # Edit the message containing the buttons with the new content, and
                # remove all the attached components.
                await ctx.respond("Button pressed!", edit=True, components=[])
                # Stop listening for additional interactions for this menu
                ctx.stop_interacting()

        class MyCommand(lightbulb.SlashCommand, name="test, description="test"):
            @lightbulb.invoke
            async def invoke(self, ctx: lightbulb.Context, client: lightbulb.Client) -> None:
                menu = MyMenu()
                resp = await ctx.respond("Menu testing", components=menu)

                # Run the menu, and catch a timeout if one occurs
                try:
                    await menu.attach(client, wait=True, timeout=30)
                except asyncio.TimeoutError:
                    await ctx.edit_respond(resp, "Timed out!", components=[])

.. warning::
    You should **always** pass a timeout, unless you wish the menu to be persistent. If you do not set a timeout,
    then the number of active menus will grow forever, along with the memory usage of your program.

.. warning::
    There are no checks added to menus by default to ensure that only one user can interact with any menu. If you
    wish to restrict a menu to only a single user (or add other checks) you should pass any state to the menu
    constructor and run your check at the top of each component callback.

.. important::
    It is recommended that you create a new instance of your menu every time you send it for the first time - otherwise
    multiple invocations could potentially interact with each other in unexpected ways.

Once you have sent your menu, and it is processing interactions, you can safely modify the menu from within your
component callbacks in any way - change attributes of the components, add components, remove components, etc. If,
within a component callback, you wish to resend the menu with a response (after changing anything) - you can pass
``rebuild_menu=True``, or ``components=self`` to the context respond call .

A Note on Select Components
^^^^^^^^^^^^^^^^^^^^^^^^^^^

When adding a select menu to a component menu you **must** store it as an instance variable. If you do not do this
then getting the selected values for it will not be typed correctly.

You can get the selected values for a select menu using the
:meth:`~lightbulb.components.menus.MenuContext.selected_values_for` method.

.. dropdown:: Example

    .. code-block:: python

        import lightbulb

        class MyMenu(lightbulb.components.Menu):
            def __init__(self) -> None:
                self.select = self.add_text_select(["foo", "bar", "baz"], self.on_select)

            async def on_select(self, ctx: lightbulb.components.MenuContext) -> None:
                await ctx.respond(f"Selected: {ctx.selected_values_for(self.select)}")

----

Modal Handling
--------------

bar

----
"""

from lightbulb.components.base import *
from lightbulb.components.menus import *
from lightbulb.components.modals import *

__all__ = [
    "BaseComponent",
    "ChannelSelect",
    "InteractiveButton",
    "LinkButton",
    "MentionableSelect",
    "Menu",
    "MenuContext",
    "Modal",
    "ModalContext",
    "RoleSelect",
    "Select",
    "TextInput",
    "TextSelect",
    "UserSelect",
]
