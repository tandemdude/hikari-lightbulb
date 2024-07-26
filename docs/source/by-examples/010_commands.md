# Commands

While 'Commands' in Lightbulb refer to Discord's [application commands](https://discord.com/developers/docs/interactions/overview#commands), in this section we will mainly be going over _slash_ commands. Context menu commands - user and message - will be explained later.

---

## Declaration

Commands are declared using classes - one class per command. In order to declare a
command, you need to subclass of one of the provided classes:

- `lightbulb.SlashCommand`
- `lightbulb.MessageCommand` (context menu command)
- `lightbulb.UserCommand` (context menu command)

This is what a slash command declaration looks like:

```python
class YourCommand(lightbulb.SlashCommand, ...):
    ...
```

Every command must have a name; a description is also required for slash commands. This information is supplied as
named parameters in your class definition.

```python
class YourCommand(
    lightbulb.SlashCommand,
    name="test-command",
    description="a test slash command"
):
    ...
```

:::{note}
There are many other parameters that can be given when declaring commands. These are clarified in the documentation
for the different command bases mentioned above.
:::

The last thing that is required in your command declaration is an invocation method. This is a method that will be
called when the command is invoked, and is the portion of your command declaration that contains the actual command
logic. For this example, we will create a simple hello world command.

You can name this method however you wish - it doesn't have to be called invoke. However, you **must** use the
`lightbulb.invoke` decorator to mark the method as the one that will be called when the command is ran.

The method **must also** have at least one *non-self* parameter; this parameter will be given an instance of
`lightbulb.Context`, which contains all the contextual information about the command invocation.

Further parameters are optional - more on that later.

```python
class HelloWorld(
    lightbulb.SlashCommand,
    name="hello-world",
    description="Makes the bot say hello world"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("Hello World!")
```

---

## Registration

At this point, you should have correctly defined a command. However, if you run the bot and try to execute the command
in Discord, you will see that nothing shows up in the command menu. In order to fix this, we need to tell the Lightbulb
client that the command exists. For now, we will register the command directly to the Lightbulb client, but later on
you will be introduced to loaders, which can allow some more flexibility in how you set up your bot.

Similar to how we defined the invocation method, we use the `Client.register` method to tell the Lightbulb client
about our command. This method can either be used as a decorator, or as a regular method by passing the command
as an argument

Here's how that should look:

:::{tab} Decorator
```python
@client.register  # <---
class HelloWorld(
    lightbulb.SlashCommand,
    name="hello-world",
    description="Makes the bot say hello world"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("Hello World!")
```
:::

:::{tab} Method
```python
class HelloWorld(
    lightbulb.SlashCommand,
    name="hello-world",
    description="Makes the bot say hello world"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("Hello World!")

client.register(HelloWorld)  # <---
```
:::

:::{note}
You can also specify specific guilds that the command should be created in by passing the `guilds` argument, like so:
`@client.register(guilds=[1234, 5678])`

See the documentation on the method for more details.
:::

After registering the command and re-running the bot, the command should now show up in Discord, and the bot should
respond once you execute it!
