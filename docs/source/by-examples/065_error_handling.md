# Error Handling

Errors are a thing you will undoubtedly encounter during your bot development journey - this is unavoidable. 
These could be due to command hooks failing, writing some code that doesn't function as expected, or any of
countless other reasons.

Now naturally, it is not ideal for your bot to just not respond to command invocations if something goes wrong. 
It would be much better for the bot to display a message telling the user what they did/went wrong to 
allow them to fix it for next time. Error handlers allow you to do this.

Lightbulb allows you to register multiple error handlers creating a sort of 'hierarchy' that errors will be
filtered through before being printed to the console (not handled).

:::{warning}
These error handlers **only** apply to errors raised **during** command execution (and execution of any hooks
that are required for the command execution). For errors during listener invocation you should create a listener
for Hikari's `ExceptionEvent` instead.
:::

---

## Handler Specification

An error handler is any asynchronous function that takes an instance of 
{obj}`~lightbulb.exceptions.ExecutionPipelineFailedException` as its first argument. Lightbulb will attempt to
dependency-inject any further parameters. The function must also return a boolean - indicating whether the
error was handled. If the error was handled (i.e. the handler returned `True`), the error will not be propagated
through any further handlers.

---

### Example

```python
async def example_error_handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    # Return `'True' if the error was handled, otherwise 'False'.
    return True
```

---

## Registering Handlers

Error handlers can either be registered directly with the client - through the `Client.error_handler()` method,
or can be registered to loaders if you wish to define one in an extension.

When registering a handler, you can pass an integer as a priority value for that handler. Higher priority handlers
will always be executed before the error is propagated to lower priority handlers. If you add multiple handlers
with the same priority, the handlers registered first take precedence.

:::{tab} Client
```python
# Valid
@client.error_handler
# Also valid
@client.error_handler(priority=123)
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    ...

# Also valid
client.error_handler(handler, priority=123)
```
:::

:::{tab} Loader
```python
loader = lightbulb.Loader()

# Valid
@loader.error_handler
# Also valid
@loader.error_handler(priority=123)
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    ...

# Also valid
loader.error_handler(handler, priority=123)
```
:::
