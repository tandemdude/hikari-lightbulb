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

    .. code-block:: python

        import asyncio
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
                    await ctx.edit_response(resp, "Timed out!", components=[])

.. warning::
    You should **always** pass a timeout, unless you wish the menu to be persistent. If you do not set a timeout,
    then the number of active menus will grow forever, along with the memory usage of your program.

.. warning::
    There are no checks added to menus by default to ensure that only one user can interact with any menu. If you
    wish to restrict a menu to only a single user (or add other checks) you should override the
    :meth:`~lightbulb.components.menus.Menu.predicate` method of your menu class. This can be used to
    prevent invocation of button (or select) logic to disallowed users.

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

Creating a Modal
^^^^^^^^^^^^^^^^

Modals are handled in a very similar way to components. Instead of subclassing ``Menu``, you will instead
have to subclass :obj:`~lightbulb.components.modals.Modal`.

.. dropdown:: Example

    .. code-block:: python

        import lightbulb

        class MyModal(lightbulb.components.Modal):
            def __init__(self) -> None:
                ...

Adding Components to Modals
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Like menus, you can add components to modals using the relevant methods:

- :meth:`~lightbulb.components.modals.Modal.add_short_text_input`
- :meth:`~lightbulb.components.modals.Modal.add_paragraph_text_input`

Just like menus, the modal will lay the added components out into rows automatically. You can use the same methods
``next_row``, ``previous_row``, etc. to further customise how the layout is created.

When you add a component, the created component object is returned. You should store this within an instance variable
- it will be needed later in order to get the submitted value from the modal context.

.. important::
    Your modal subclass **must** implement the ``on_submit`` method. This will be called when an interaction for
    the modal is received and should perform any logic you require.

.. dropdown:: Example

    .. code-block:: python

        import lightbulb

        class MyModal(lightbulb.components.Modal):
            def __init__(self) -> None:
                self.text = self.add_short_text_input("Enter some text")

            async def on_submit(self, ctx: lightbulb.components.ModalContext) -> None:
                await ctx.respond(f"submitted: {ctx.value_for(self.text)}")

Running Modals
^^^^^^^^^^^^^^

Sending a modal with a response is similar to using a menu - you should pass the modal instance to the ``components=``
argument of ``respond_with_modal`` of the context or interaction.

Like menus, you need the Lightbulb :obj:`~lightbulb.client.Client` instance in order for it to listen for the
relevant interaction. However, unlike menus, when attaching a modal to the client it will **always** wait for the
interaction to be received before continuing. You must also pass a timeout after which an :obj:`asyncio.TimeoutError`
will be raised - if you do not pass a timeout, it will default to 30 seconds.

When attaching a modal to the client, you must pass the same custom ID you used when sending the modal response,
otherwise Lightbulb will not be able to resolve the correct interaction for the modal submission.

To get your ``Client`` instance within a command, you can use dependency injection as seen in the following example.
Check the "Dependencies" guide within the by-example section of the documentation for more details about dependency
injection.

.. dropdown:: Example

    .. code-block:: python

        import asyncio
        import uuid
        import lightbulb

        class MyModal(lightbulb.components.Modal):
            def __init__(self) -> None:
                self.text = self.add_short_text_input("Enter some text")

            async def on_submit(self, ctx: lightbulb.components.ModalContext) -> None:
                await ctx.respond(f"submitted: {ctx.value_for(self.text)}")

        class MyCommand(lightbulb.SlashCommand, name="test", description="test"):
            @lightbulb.invoke
            async def invoke(self, ctx: lightbulb.Context, client: lightbulb.Client) -> None:
                modal = MyModal()

                # Using a uuid as the custom ID for this modal means it is very unlikely that there will
                # be any custom ID conflicts - if you used a set value instead then it may pick up a submission
                # from a previous or future invocation of this command
                await ctx.respond_with_modal("Test Modal", c_id := str(uuid.uuid4()), components=modal)
                try:
                    await modal.attach(client, c_id)
                except asyncio.TimeoutError:
                    await ctx.respond("Modal timed out")

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
    "MenuHandle",
    "Modal",
    "ModalContext",
    "RoleSelect",
    "Select",
    "TextInput",
    "TextSelect",
    "TextSelectOption",
    "UserSelect",
]
