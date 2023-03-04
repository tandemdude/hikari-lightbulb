==========
Components
==========

Message components (buttons and select menus) are a good way to take additional input from the user. For example,
confirming actions using buttons, or selecting a category of a help command to display using a select menu.

Hikari supports message components, albeit using them with raw Hikari is not the most convenient experience. For
this reason, you may wish to look into an alternate third party library such as
`hikari-miru <https://github.com/HyperGH/hikari-miru>`_ or `hikari-yuyo <https://github.com/FasterSpeeding/Yuyo>`_
which provide utilities to allow you to use components more easily.

In order to add components to a message, you must create an action row - think of this like a group of components. A
single message can have up to 5 action rows, and each action row can have up to 5 buttons, or a single select
menu.

Creating Components
-------------------

Creating an action row is relatively simple, Hikari provides a builder which is instantiated by calling a method
on your bot's REST client.

.. code-block:: python

    # Bot is assumed to be an instance of GatewayBot or a subclass
    row = bot.rest.build_message_action_row()

To add a button to the action row, the method ``add_button`` is used. Likewise, ``add_select_menu`` is used to add
a select menu to the row. The following examples will only be for buttons, however select menus are very similar
so you should be able to figure that out on your own should you need to.

Buttons are built using a similar builder syntax to an action row. The different properties are set using their
individual respective methods, for example ``set_label``, ``set_is_disabled``, etc. All available methods can be seen
on the hikari documentation.

.. code-block:: python

    # Creating the button builder. The add_button method takes two arguments, 'style' and 'url_or_custom_id'.
    # If you provide a url, the style **must** be ButtonStyle.LINK. The custom ID will be useful later when we
    # want to process interactions triggered by the button.
    # The below example will be a blurple button with custom ID 'foo'.
    button = row.add_button(hikari.ButtonStyle.PRIMARY, "foo")
    # Set the button's label
    button.set_label("foo")
    # Add the button to the action row. This **must** be called after you have finished building every
    # individual component.
    button.add_to_container()

The created action row(s) are added to the message through passing a value to the ``component`` or ``components`` kwarg
of any method that creates a message. If you have a single action row, you can pass it directly to ``component``,
otherwise you should pass a list of your action rows to ``components``.

Handling Component Interactions
-------------------------------

When a component is interacted with, discord sends an
`InteractionCreateEvent <https://www.hikari-py.dev/hikari/events/interaction_events.html#hikari.events.interaction_events.InteractionCreateEvent>`_
either through the gateway, or to your interaction server (if one has been set up). The type of ``event.interaction``
will **always** be
`ComponentInteraction <https://www.hikari-py.dev/hikari/interactions/component_interactions.html#hikari.interactions.component_interactions.ComponentInteraction>`_
for a component interaction. Note that an interaction **will not** be sent for link buttons.

When receiving a component interaction, we can use the custom ID we set earlier in order to know how to respond to the
interaction.

The below example will use a permanent listener, but you could just as easily use a ``wait_for`` or ``stream`` if you
only want to allow the component to be interacted with temporarily.

.. code-block:: python

    # Interaction create listener
    @bot.listen(hikari.InteractionCreateEvent)
    async def on_component_interaction(event: hikari.InteractionCreateEvent) -> None:
        # Filter out all unwanted interactions
        if not isinstance(event.interaction, hikari.ComponentInteraction):
            return

        if event.interaction.custom_id == "foo":
            await event.interaction.create_initial_response(
                hikari.ResponseType.MESSAGE_CREATE,  # Create a new message as response to this interaction
                "bar",  # Message content
                flags=hikari.MessageFlag.EPHEMERAL  # Ephemeral message, only visible to the user who pressed the button
            )

.. note::
    Once you receive an interaction, you have 3 seconds to send your initial response. This can be extended using
    a deferred response type. See all available response types on the Hikari documentation.
