# Context Menus

Context menu commands appear when right-clicking on either a message or user within Discord. This allows you to invoke
commands directly without having to receive options from the user. For example, you could have a command for a currency
bot that let you directly view the balance of another user by right-clicking on them and running `Apps -> Get Balance`.

Unfortunately, discord limits you to very few of these commands but they can still be useful in certain situations.

:::{note}
Context menu commands cannot have a description - you only need to provide a name when declaring one.
:::

---

## Message Commands

A message command shows up in the context menu when right-clicking on a sent message. When invoked, these commands
are provided with the message that the command was executed on. This message is a pseudo-option and so similarly to
slash commands, you can get the value by accessing `self.target` within the command callback.

```python
class GetMessageId(
    lightbulb.MessageCommand,
    name="Get ID",
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        # 'self.target' contains the message object the command was executed on
        await ctx.respond(self.target.id)
```

---

## User Commands

A user command shows up in the context menu when right-clicking on a user. When invoked, these commands
are provided with the user that the command was executed on. This user is a pseudo-option and so similarly to
slash commands, you can get the value by accessing `self.target` within the command callback.

```python
class GetUserId(
    lightbulb.UserCommand,
    name="Get ID",
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        # 'self.target' contains the user object the command was executed on
        await ctx.respond(self.target.id)
```

:::{warning}
With context menu commands, Discord seems to be quite frugal with the amount of properties that it populates
on the resolved objects. This means that you may need to re-fetch the object using the REST API if you need
one of the properties that is not available.
:::
