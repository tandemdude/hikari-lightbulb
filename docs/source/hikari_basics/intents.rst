=======
Intents
=======

.. note::
    This page does not aim to explain all the different Intents along with what events each of them
    enable, for information on this you should refer to the `Discord documentation <https://discord.com/developers/docs/topics/gateway#gateway-intents>`_
    and the `Hikari documentation <https://www.hikari-py.dev/hikari/intents.html#hikari.intents.Intents>`_

During development of your bot, you may have encountered the following warning:

.. code-block::

    W 2022-01-29 01:06:33,243 py.warnings: path/to/your/file.py:23: MissingIntentWarning: You have tried to listen to SomeEvent, but this will only ever be triggered if you enable one of the following intents: SOME_INTENTS.

You may also have encountered certain aspects of the cache not containing entries where you would usually expect them
to be present. For example: empty member cache, or presences cache.

The default intents given to the bot, if you do not override the value with your own, are present in the ``Intents``
enum `hikari.Intents.ALL_UNPRIVILEGED <https://www.hikari-py.dev/hikari/intents.html#hikari.intents.Intents.ALL_UNPRIVILEGED>`_.

This **does not** include the intents that you have to enable on the Discord developer portal in order to be able to use,
for example, the ``GUILD_MEMBERS`` intent.

You can pass your own intents to hikari's ``GatewayBot`` constructor, and so it follows that you can also pass your own
intents to lightbulb's ``BotApp`` constructor.

.. code-block:: python

    # Hikari only
    import hikari
    bot = hikari.GatewayBot(intents=hikari.Intents.ALL)

    # Lightbulb
    import lightbulb
    bot = lightbulb.BotApp(intents=hikari.Intents.ALL)

To enable all gateway intents, you should pass ``hikari.Intents.ALL`` to the bot's constructor, however you should note
that the privileged intents **must** be enabled on the developer portal or an error will be raised when the bot starts.
You should also note that once your bot reaches the verification threshold (80 guilds), you will need to provide discord
with evidence that your bot requires the requested intents in order for you to be able to use them when the bot is verified.

Instead of passing ``hikari.Intents.ALL``, you can also pass any arbitrary combination of intents as the ``Intents`` enum
is a bitfield. To create your own combination of intents you should use the bitwise ``OR`` (``|``) operator.

.. code-block:: python

    import hikari

    my_intents = (
        hikari.Intents.GUILD_MESSAGES
        | hikari.Intents.DM_MESSAGES
        | hikari.Intents.GUILD_BANS
        | ...
    )

If you have any further questions on any points mentioned here feel free to join the `Hikari Discord Server <https://discord.gg/Jx4cNGG>`_ where
other developers will be happy to help you with your queries.
