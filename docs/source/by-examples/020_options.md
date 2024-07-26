# Options

Now that you've managed to make a basic command and have your bot respond to the users, it would probably be useful to
take some form of input. For slash commands, this is done using options.

Note that context menu commands **cannot** have options - see the context menu section for more on how they work.

---

## Adding an Option

Options are defined as class variables in your command class. Lightbulb provides various methods to help you
create options of different types. For now we will just focus on string options - other types will be mentioned
later.

All options **must** have a name and description, other parameters are optional and specific to each
type of option.

A simple command with a string option would look like this:

```python
class YourCommand(
    lightbulb.SlashCommand,
    ...
):
    # Simple string option.
    text = lightbulb.string("text", "text option")
    
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        ...
```

:::{note}
Options are added to commands in the order they are defined in the class. Any options that are not required (i.e. have
a default value) must appear **after** required options.
:::

---

## Using an Option

You should understand how to add options to commands now - it would probably be useful to get the value the user
supplied from within the command invocation function. This is simply done by accessing the option variable through
`self`. I.e. in the above example, `self.text`.

A simple 'echo' command to repeat the given text using a string option could look like this:

```python
class Echo(
    lightbulb.SlashCommand,
    name="echo",
    description="echo",
):
    text = lightbulb.string("text", "the text to repeat")
    
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(self.text)
```

---

## Option Types

Lightbulb supports the same option types natively supported by discord. These are:
- string
- integer
- boolean
- number (float)
- user
- channel
- role
- mentionable
- attachment

Usage of each of the supported option types are the same as shown above using the string option.

```python
class YourCommand(
    lightbulb.SlashCommand,
    ...
):
    string = lightbulb.string(...)
    integer = lightbulb.integer(...)
    boolean = lightbulb.boolean(...)
    number = lightbulb.number(...)
    user = lightbulb.user(...)
    channel = lightbulb.channel(...)
    role = lightbulb.role(...)
    mentionable = lightbulb.mentionable(...)
    attachment = lightbulb.attachment(...)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        ...
```

---

## Common Pitfalls

- Due to JavaScript quirks, an `integer` option **cannot** be used if you wish to take a discord ID. You should use a
  `string` option instead - assuming none of the other option types are more suitable.
- Commands can have a maximum of 25 options. Any more than that and discord will error when Lightbulb tries to sync
  the commands with Discord.
