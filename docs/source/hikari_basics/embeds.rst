======
Embeds
======

Creating embeds is trivial using Hikari. If you have used ``discord.py`` the method will feel very similar
to what you are used to.

First you need to create an instance of the ``hikari.Embed`` class:

.. code-block:: python

    import hikari

    embed = hikari.Embed()

In the embed constructor you can pass values for the embed ``title``, ``description``, ``url``, ``colour``, and ``timestamp``. See
the `Embed documentation <https://www.hikari-py.dev/hikari/embeds.html#hikari.embeds.Embed>`_ for details on the
constructor signature. All arguments to the constructor **must** be passed as keyword arguments.

Other embed properties are set/added through various calls to the methods of the ``Embed`` class. These include:
``add_field``, ``set_author``, ``set_footer``, ``set_image`` and ``set_thumbnail``. These methods can also be chained
together if you so desire.

Below is an example embed:

.. code-block:: python

    import hikari

    embed = hikari.Embed(title="Example embed", description="An example hikari embed")
    embed.add_field("Field name", "Field content (value)")
    embed.set_thumbnail("https://i.imgur.com/EpuEOXC.jpg")
    embed.set_footer("This is the footer")

Or using chained calls:

.. code-block:: python

    embed = (
        hikari.Embed(title="Example embed", description="An example hikari embed")
        .add_field("Field name", "Field content (value)")
        .set_thumbnail("https://i.imgur.com/EpuEOXC.jpg")
        .set_footer("This is the footer")
    )

To send an embed, you can pass the embed into either the ``content`` or ``embed`` argument to the relevant message
creation method. An example using a lightbulb command can be seen below:

.. code-block:: python

    import lightbulb
    import hikari

    @lightbulb.command("embed", "Sends an embed in the command channel")
    @lightbulb.implements(...)
    async def embed_command(ctx: lightbulb.Context) -> None:
        embed = hikari.Embed(title="Example embed", description="An example hikari embed")
        embed.add_field("Field name", "Field content (value)")
        embed.set_thumbnail("https://i.imgur.com/EpuEOXC.jpg")
        embed.set_footer("This is the footer")
        await ctx.respond(embed)  # or respond(embed=embed)

If you have any further questions on any points mentioned here feel free to join the `Hikari Discord Server <https://discord.gg/Jx4cNGG>`_ where
other developers will be happy to help you with your queries.
