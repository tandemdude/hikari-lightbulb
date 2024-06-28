(dependencies)=
# Dependencies

Now that your bot is coming along nicely, you are likely thinking about adding some features that may require
data storage (i.e. a database) - or maybe you are using an API you need a client for. In these cases,
a database or API client would be considered a **dependency**.

Lightbulb includes a [dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) framework to help 
you manage the different dependencies required by you bot to function. This allows you to forget about 
having to keep global state or pass objects around throughout your application and have the dependencies 
"magically appear" when you need them.

## Registration

Before a dependency can be used by you application it need to be registered with the Lightbulb client. This
is done using the `Client.di.register_dependency` method. Dependencies are lazily-initialised when they are
required so in order to register a dependency you need to provide a factory method which creates that dependency.

The factory method may be a synchronous or an asynchronous function, but cannot take
any arguments. See below for an exmaple using `aiohttp.ClientSession`.

```python
import aiohttp

client.di.register_dependency(aiohttp.ClientSession, lambda: aiohttp.ClientSession())
```

::::{tip}
Lightbulb registers some dependencies for you automatically depending on what type of application you pass when creating
the client. You can see these below.

:::{tab} GatewayBot
- `lightbulb.Client`
- `hikari.GatewayBot`
- `hikari.api.RESTClient`
- `hikari.api.EventManager`
:::
:::{tab} RESTBot
- `lightbulb.Client`
- `hikari.RESTBot`
- `hikari.api.RESTClient`
- `hikari.api.InteractionServer`
:::
::::

## Injection

Once you have registered some dependencies, you probably want to be able to use them somewhere in the application.

Lightbulb's dependency injection relies on an injection context being available when the method that requires
dependencies is called. Most of the time you do not need to have to worry about setting this up - if the dependency
is requested during a Lightbulb-managed flow (i.e. command invocation, autocomplete, error handling) then a context
will always be available.

If, for some reason, you need to set up this context manually, you can do so using the provided context manager
`lightbulb.di.ensure_di_context(Client)`. But we won't worry about that for now.

Lightbulb will enable dependency injection on a specific subset of your methods for you when using specific decorators.

These are listed below:
- `@lightbulb.invoke`
- `@Client.register`
- `@Client.error_handler`
- `@Loader.command` (due to it calling `Client.register` internally)
- `@Loader.listener`

If you need to enable dependency injection on other functions, you can decorate it with `@lightbulb.with_di` - from
then on, each time the function is called, lightbulb will attempt to dependency inject suitable parameters.

:::{note}
For a parameter to be suitable for dependency injection, it needs to match the following rules:
- It **must** have a type annotation
- It has no default value, or a default value of exactly `lightbulb.INJECTED`
- It **cannot** be positional-only (injected parameters are always passed using keywords)
:::

Simple example using the `aiohttp.ClientSession` registered before:

```python
class ExampleCommand(lightbulb.SlashCommand, name="example", description="example"):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cs: aiohttp.ClientSession):
        # The 'cs' parameter will be injected upon the command being called
        ...
```

## Usage Example

Now a full worked example with a working command you should be able to drop straight into your own bot.

```python
import aiohttp
import hikari
import lightbulb

# Returns a random 200x200 image when fetched with a GET request
RANDOM_IMAGE_URL = "https://picsum.photos/200"

# Initialise the bot and Lightbulb client
bot = hikari.GatewayBot("your token")
client = lightbulb.client_from_app(bot)
bot.subscribe(hikari.StartingEvent, client.start)

# Register the dependency we want to use later
client.di.register_dependency(aiohttp.ClientSession, lambda: aiohttp.ClientSession())


# Register a stopping listener to clean up the dependency at the end of the bot's lifecycle
# This isn't strictly necessary - but best practice when dealing with database clients or similar
@bot.listen(hikari.StoppingEvent)
async def on_stopping(_: hikari.StoppingEvent) -> None:
    cs = await client.di.get_dependency(aiohttp.ClientSession)
    await cs.close()


@client.register
class RandomImage(
    lightbulb.SlashCommand,
    name="random-image",
    description="Generates a random image using the picsum API"
):
    # The 'lightbulb.invoke` decorator enables dependency injection on the function, so we
    # do not need to include the 'lightbulb.with_di' decorator here
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cs: aiohttp.ClientSession) -> None:
        # Fetch the image using the injected ClientSession dependency
        async with cs.get(RANDOM_IMAGE_URL) as resp:
            image = await resp.read()
        # Respond to the command with the image
        await ctx.respond(hikari.Bytes(image, "image.jpg"))


# Run the bot
bot.run()
```

## Cleanup

As seen in the previous worked example, you should probably consider cleaning up dependencies
at the end of the bot's lifecycle to make sure you do not leave any hanging connections or other resources.

Lightbulb does not define a specific way that you should do this - it is left up to the reader. A good
method for this is using a `hikari.StoppingEvent` (or `hikari.StoppedEvent`) listener or using
`hikari.RESTBot.add_shutdown_callback` depending on the bot implementation you are using.

Listeners by themselves are not dependency injected, so you may need to use the previously seen 
`Client.di.get_dependency` method to retrieve the created dependencies instead. Refer to the previous section
to see an example on how dependency cleanup could be implemented.

:::{note}
The `Client.di.get_dependency` method **does not** require a dependency injection context to
be present due to it fetching the dependencies directly from the client, so it can be called
whenever the client is available.
:::

## Disabling Dependency Injection

If you wish to run your application with no dependency injection, Lightbulb allows you
to disable the entire system by setting the environment variable `LIGHTBULB_DI_DISABLED` to `false`.

This will prevent decorators from wrapping functions to enable DI and will prevent parameter processing
from attempting to resolve injectable parameters.
