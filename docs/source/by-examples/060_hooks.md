# Hooks

Hooks are a way to perform extra logic before and after a command is invoked. This is done using the concept of
an 'execution pipeline' that has several steps which are executed in order when the user calls a command
from within discord.

All the steps must complete successfully in order for a command invocation to be considered complete. If any one
of the hooks fails for any of the steps, the pipeline fails and an error will be thrown.

---

## Creating a Hook

Hooks are created using the `lightbulb.hook` decorator. They can be either synchronous or asynchronous functions - both
will work. When creating a hook, you must specify the step that it runs on, and you can optionally specify
whether the hook should be skipped if the pipeline has already failed.

By default, all hooks will always run no matter whether the pipeline has failed or not - the exception is the 
command invocation function, which will never be executed if any preceding hooks have failed. Pass 
`skip_when_failed=True` to the hook decorator to avoid execution of the hook if the pipeline has already failed.

To fail the pipeline, hooks can raise any exception. This will be caught and re-raised as an
`ExecutionPipelineFailedException` once any remaining hooks have been run.

Below is an example hook that checks if the person who invoked the command is me (thomm.o) and will fail otherwise.

```python
@lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
def fail_if_not_thommo(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    if ctx.user.id != 215061635574792192:
        raise RuntimeError("only thomm.o can use this command")
```

As seen above, hooks must take at least 2 arguments - the execution pipeline being run, and the context that the
command was invoked under. Lightbulb will attempt to dependency-inject any further arguments.

---

## Adding Hooks to Commands

Adding hooks to commands is very simple - you just pass them to the `hooks` class parameter.

```python
class YourCommand(
    lightbulb.SlashCommand,
    ...,
    hooks=[fail_if_not_thommo]
):
    ...
```

When the command is invoked, hooks will be executed in the order they are defined, grouped by execution step.

---

## Step Order

Lightbulb provides a default step order - however, you can specify your own custom one when the `Client` is created
which will cause command execution to follow your defined steps instead. 

- The default order is exported as `lightbulb.DEFAULT_EXECUTION_STEP_ORDER` if you wish to augment it when creating your own.
- The provided execution steps are contained within `lightbulb.ExecutionSteps` if you wish to use them.

:::{warning}
Custom orders **must** contain the step `lightbulb.ExecutionStep.INVOKE` otherwise the command invocation callback
will never be run. Hooks also **cannot** be added for this step and will throw an error if you try to do so.
:::

---

## Custom Steps

Creating your own custom execution step is very simple and supported out-of-the-box by Lightbulb. All you have to
do is create an instance of `ExecutionStep` with a custom ID. Note that all step IDs must be unique - you cannot
define a new step with the same ID as an existing one.

```python
YOUR_STEP = lightbulb.ExecutionStep("YOUR_STEP_ID")
```

---

## Worked Custom Step Example

As a demo example for customizing the execution step order and defining a custom step, we are going to implement
automatic deferral of command responses before any other steps are run.

```python
import hikari
import lightbulb

# Define our custom execution step
AUTO_DEFER = lightbulb.ExecutionStep("AUTO_DEFER")

bot = hikari.GatewayBot(...)
client = lightbulb.client_from_app(
    bot,
    # Add our custom step to the step order. Our step will run first, followed by all the
    # default steps lightbulb would usually use.
    execution_step_order=[AUTO_DEFER, *lightbulb.DEFAULT_EXECUTION_STEP_ORDER]
)
bot.subscribe(hikari.StartingEvent, client.start)


# Define our hook to defer the command response
@lightbulb.hook(AUTO_DEFER)
async def auto_defer_command_response(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    await ctx.defer()


@client.register
class AutoDeferredCommand(
    lightbulb.SlashCommand,
    name="auto-defer",
    description="auto defer test",
    # Add our hook to the command
    hooks=[auto_defer_command_response]
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("This command was auto-deferred!")


bot.run()
```

---

## Hook Inheritance

Sometimes, you may find yourself frequently adding the same hooks to all your commands. Lightbulb allows you to
pass some common hooks when creating your client which will then be applied to **all** commands registered
to the client upon invocation.

For example, if you want all your commands to only be usable by yourself then you could do the following:

```python
# Define the hook
@lightbulb.hook(lightbulb.ExecutionSteps.CHECKS)
async def only_me(_: lightbulb.ExecutionPipeline, ctx: lightbulb.Context) -> None:
    if ctx.user.id != YOUR_USER_ID:
        raise RuntimeError("you are not allowed to use the command")

# Add the hook to the client
client = lightbulb.client_from_app(..., hooks=[only_me])

# This command will only be usable by you!
@client.register
class YourCommand(...):
    ...
```
