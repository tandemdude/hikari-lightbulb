# Dependencies

Now that your bot is coming along nicely, you are likely thinking about adding some features that may require
data storage (i.e. a database) - or maybe you are using an API you need a client for. In these cases,
a database or API client would be considered a **dependency**.

Lightbulb includes a [dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) (DI) framework
implemented using [`linkd`](https://github.com/tandemdude/lightbulb) to help 
you manage the different dependencies required by your bot to function. This allows you to forget about 
having to keep global state or pass objects around throughout your application and have the dependencies 
"magically appear" when you need them.

::::{dropdown} TL;DR
You can provide dependencies to any part of your application using dependency injection. If the code is being executed
during a command execution, listener invocation (loaders only), error handler, or task, then DI is available.

Let us assume you want to provide an {obj}`aiohttp.ClientSession` that is accessible in any DI enabled function.

0. **Prequisites (hikari bot and lightbulb client)**

```python
import hikari
import lightbulb

bot = hikari.GatewayBot("YOUR_TOKEN")
client = lightbulb.client_from_app(bot)

bot.subscribe(hikari.StartingEvent, client.start)
```

1. **Register your dependency**

```python
import aiohttp

client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_factory(
    aiohttp.ClientSession, lambda: aiohttp.ClientSession()
)
```

2. **Use the dependency**

```python
@client.register
class YourCommand(...):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cs: aiohttp.ClientSession) -> None:
        # The 'cs' parameter was passed the client session for you to use in your function
        ...
```

3. **Done! It's really that simple!**

:::{seealso}
- {ref}`auto-registered-dependencies`
- {ref}`enabling-injection`
- {ref}`cleanup`
:::

The rest of this page is geared more towards advanced users that wish to be able to use the dependency injection 
to its full potential. It is much more powerful than outlined in the example above and can enable 
some more advanced techniques during development of your bot.

Try not to get overwhelmed, and if you have problems understanding anything don't be afraid to ask for help in 
the Discord server.
::::

---

## How the DI System Works

Lightbulb's dependency injection works using a context hierarchy. Later contexts inherit the dependencies of earlier
ones, but can also have their own dependencies that are lifecycled alongside the topmost context. The base context -
called `DEFAULT` - is what contains the 'globally' available dependencies. All further contexts are derived from
this base context.

Lightbulb provides 5 different contexts by default, each available under specific circumstances only. These are:
- {obj}`~lightbulb.di.Contexts.DEFAULT` - always available during all Lightbulb controlled flows
- {obj}`~lightbulb.di.Contexts.COMMAND` - available only during command execution (including hooks and 
  error handlers)
- {obj}`~lightbulb.di.Contexts.AUTOCOMPLETE` - available only during autocomplete handler execution
- {obj}`~lightbulb.di.Contexts.LISTENER` - available only during listener execution; specifically only 
  available for listeners registered to `Loader`s
- {obj}`~lightbulb.di.Contexts.TASK` - available only during task execution.

The diagram below represents a simplified version of how Lightbulb handles function calls that require dependency
injection. A 'Flow' is something that has its own context allocated to it. Commands, autocomplete, etc - as
outlined above.

::::{div} only-light
:::{mermaid}
%%{init: {'theme':'light'}}%%
sequenceDiagram
    participant Client
    participant Flow
    participant FlowContext
    participant Method

    Client ->> Client: Enter default context
    loop Command, autocomplete, listener, task, etc.
        Client ->>+ Flow: Start flow
        Flow -->>+ FlowContext: Enter flow-specific context
        Flow ->>+ Method: Call injection-enabled method
        Method -->> FlowContext: Resolve dependencies
        FlowContext -->> Method: Provide dependencies
        Method ->> Method: Invoke
        Method ->>- Flow: Return result
        FlowContext -->>- Flow: Cleanup flow-specific context
        Flow ->>- Client: End Flow
    end
    Client ->> Client: Cleanup default context
:::
::::
::::{div} only-dark
:::{mermaid}
%%{init: {'theme':'dark'}}%%
sequenceDiagram
    participant Client
    participant Flow
    participant FlowContext
    participant Method

    Client ->> Client: Enter default context
    loop Command, autocomplete, listener, task, etc.
        Client ->>+ Flow: Start flow
        Flow -->>+ FlowContext: Enter flow-specific context
        Flow ->>+ Method: Call injection-enabled method
        Method -->> FlowContext: Resolve dependencies
        FlowContext -->> Method: Provide dependencies
        Method ->> Method: Invoke
        Method ->>- Flow: Return result
        FlowContext -->>- Flow: Cleanup flow-specific context
        Flow ->>- Client: End Flow
    end
    Client ->> Client: Cleanup default context
:::
::::

---

## Registering and Resolving

The dependency injection system stores dependencies in objects called 'registries'. These contain the instructions
that allow 'containers' to create and supply the dependencies when they are required. Registries on their own
cannot provide dependencies.

To register a dependency you first need to get the registry for the context you want to add the dependency for, and 
then register the dependency with the registry. For example, registering an `aiohttp.ClientSession` that you want
to be available throughout the entire client lifecycle.

```python
import aiohttp

import lightbulb

client = lightbulb.client_from_app(...)
# Get the registry for the default context
registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)
# Register our new dependency
registry.register_factory(aiohttp.ClientSession, lambda: aiohttp.ClientSession())
```

:::{important}
Ideally, you should register **all** your dependencies before the client is started, as once a container is created
for a registry - that registry is frozen and no new dependencies can be registered to it. There is a way to get
around this - mentioned later - but try to make sure that all your dependencies are registered ahead-of-time.
:::

(auto-registered-dependencies)=
### Automatically Registered Dependencies

Lightbulb registers some dependencies for you by default for each of the different contexts. These are as followed:

| DEFAULT                 | COMMAND                       | AUTOCOMPLETE                    |
|-------------------------|-------------------------------|---------------------------------|
| `lightbulb.Client`      | `lightbulb.Context`           | `lightbulb.AutocompleteContext` |
| `hikari.api.RESTClient` | `lightbulb.ExecutionPipeline` |                                 |

Additionally, when using either `hikari.GatewayBot` or `hikari.RESTBot`, the following dependencies are registered
for the `DEFAULT` context:

:::{tab} GatewayBot
- `hikari.GatewayBot`
- `hikari.api.EventManager`
:::
:::{tab} RESTBot
- `hikari.RESTBot`
- `hikari.api.InteractionServer`
:::

### Dependencies with Dependencies

When registering a dependency, you can either register it by factory or by value. If registering by factory, the
given factory method is permitted to require dependencies of its own - they will be fulfilled before that dependency
is supplied. For example, lets say we have a configuration class that contains the base URL we want to pass to our
`ClientSession`.

```python
import aiohttp

import lightbulb


class Config:
    base_url: str

client = lightbulb.client_from_app(...)
registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)
registry.register_value(Config, Config())

# Define the factory dependencies using type hints.
# A valid factory must pass all the following conditions for every parameter:
# - MUST not have a default value, unless the default value is exactly 'lightbulb.di.INJECTED'
# - MUST not be positional only, var positional (*args), or var keyword (**kwargs)
# - SHOULD have a type-hint. If no type-hint provided, a dependency will attempt to be resolved from the parameter name
#   ^^^ this **ONLY** applies to factory methods - for injectable methods, type-hints MUST be provided
def create_client_session(cfg: Config) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(cfg.base_url)

registry.register_factory(aiohttp.ClientSession, create_client_session)
```

If you try to register a dependency whose factory directly depends on itself, a 
{obj}`~linkd.exceptions.CircularDependencyException` will be raised.

### Multiple Dependencies of the Same Type

As you have seen above, when registering a dependency you must tell the registry what type to register that dependency
as. Above we have only used concrete types, but Lightbulb also supports using {obj}`typing.NewType` to create
a new type to represent your dependency. This can be useful if you need to maintain connections to multiple
databases or similar etc.

```python
from typing import NewType

import aiohttp

import lightbulb

client = lightbulb.client_from_app(...)
registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)
# Create a new type to represent your dependency
ClientSession1 = NewType("ClientSession1", aiohttp.ClientSession)
ClientSession2 = NewType("ClientSession2", aiohttp.ClientSession)
# Register the dependencies
registry.register_factory(ClientSession1, lambda: aiohttp.ClientSession())
registry.register_factory(ClientSession2, lambda: aiohttp.ClientSession())

# You must then refer using the new type where you want them to be injected
# For this reason it is recommended you define the new types within a separate file, so they can be easily reused
@lightbulb.di.with_di
async def example(cs1: ClientSession1, cs2: ClientSession2) -> None:
    ...
```

:::{note}
If you are using Python 3.12 or higher, you can also use a
[type statement](https://docs.python.org/3/reference/simple_stmts.html#type) to create the new type.

```python
import aiohttp

# The same as using 'NewType' above
type ClientSession1 = aiohttp.ClientSession
type ClientSession2 = aiohttp.ClientSession
```
:::

### Ephemeral Dependencies

Before understanding ephemeral (temporary) dependencies, you first need to understand how dependencies are provided
to the application during runtime. This is done using dependency 'containers'. When created, containers are given
a registry that the container can provide dependencies from. As mentioned before, once created, the registry backing
the container is frozen and hence cannot have additional dependencies registered to it.

There is however a method to register additional dependencies directly with the container once it has been created.
For example, Lightbulb registers the command context this way as it is not possible for it to be created from a
factory or the value known beforehand.

Any dependency directly registered with a container is known as an ephemeral dependency. These dependencies follow
the lifecycle of the container and are destroyed once the container is closed. You can register an ephemeral dependency
using either of the following methods:
- {meth}`.Container.add_value`
- {meth}`.Container.add_factory`

Getting the current active container in order to add an ephemeral dependency to it will be addressed in the next section.

### Overriding Dependencies and Scoped Resolution

As mentioned before, Lightbulb provides multiple injection contexts that you can register dependencies to. Each of these
contexts has a different lifetime for the container's created from them, which corresponds to the type of context.

- {obj}`~lightbulb.di.Contexts.DEFAULT` - the entire length of the application
- {obj}`~lightbulb.di.Contexts.COMMAND` - the entire length of a command execution, including execution of all hooks
  and error handlers. A new {obj}`~linkd.container.Container` will be created for each distinct command invocation.
- {obj}`~lightbulb.di.Contexts.AUTOCOMPLETE` - the entire length of an autocomplete execution. A new
  {obj}`~linkd.container.Container` will be created for each distinct autocomplete invocation.
- {obj}`~lightbulb.di.Contexts.LISTENER` - the entire length of a listener execution. A new
  {obj}`~linkd.container.Container` will be created for each distinct listener invocation.
- {obj}`~lightbulb.di.Contexts.TASK` - the entire length of a task execution. A new
  {obj}`~linkd.container.Container` will be created for each distinct invocation of each task.

Overriding dependencies occurs when a child container has a dependency of the same type defined in the parent
container - either ephemerally, or from the child's registry. Any injection done using the child container
will then use the overridden value instead of the original from the parent. Any dependencies defined in the
parent **CANNOT** access the new overridden one.

:::{dropdown} Scoped Dependency Resolution
1. **Providing Dependencies:**

   A container (think of it as a box) holds and provides various dependencies (think of these as tools).
   For example, the {const}`~linkd.context.DefaultContainer` might provide a `DatabaseService`.

2. **Dependencies with Their Own Dependencies:**

   Some dependencies need other dependencies to function. For example, a `UserService` might require a `DatabaseService`.

3. **Parent-Child Container Relationship:**

   Containers can have hierarchical relationships. A {const}`~lightbulb.di.CommandContainer` will inherit
   dependencies from the {const}`~linkd.solver.DefaultContainer`, as all context-specific containers are created
   with the {const}`~linkd.solver.DefaultContainer` as the base.

4. **Overriding Dependencies in Child Containers:**

   If a {const}`~lightbulb.di.CommandContainer` defines a dependency with the same type as the
   {const}`~linkd.DefaultContainer`, this is called overriding. Only dependencies within the 
   {const}`~lightbulb.di.CommandContainer` and any of its children can access the overridden value.

5. **Resolving Dependencies:**

   - When trying to resolve a dependency, a container first looks in its own scope.
   - It can also look into its child containers if needed.
   - It **never** looks into its parent containers for dependencies.
:::

:::{dropdown} Theoretical Example
An example container structure

```
MainContainer
    |- DatabaseService
    |- LoggingService
    |- ChildContainer
        |- DatabaseService (overridden)
        |- UserService (depends on DatabaseService)
```

1. **Initial Setup:**

   `MainContainer` provides `DatabaseService` and `LoggingService`. `ChildContainer` is derived from `MainContainer`.

2. **Overriding Dependency:**

   `ChildContainer` overrides `DatabaseService` with a new configuration.

3. **Dependency Resolution:**

   `UserService` in `ChildContainer` will use the `DatabaseService` provided by `ChildContainer`, not `MainContainer`.
   `LoggingService` in `ChildContainer` will still use the `LoggingService` from `MainContainer` since it was not overridden.
:::

---

## Injection

Once you have registered some dependencies, you probably want to be able to use them somewhere in the application.

### Injection Context

Lightbulb's dependency injection relies on an injection context being available when the method that requires
dependencies is called. Most of the time you do not need to have to worry about setting this up - if the dependency
is requested during a Lightbulb-managed flow (i.e. command invocation, autocomplete, error handling) then a context
will always be available.

If, for some reason, you need to set up this context manually, you can do so using the provided context manager
{meth}`.DependencyInjectionManager.enter_context` (using the client's DI 
manager, {attr}`.Client.di`).

(enabling-injection)=
### Enabling Injection

Lightbulb will enable dependency injection on a specific subset of your methods for you when using specific decorators.

These are listed below:
- {meth}`@lightbulb.invoke <lightbulb.commands.execution.invoke>`
- {meth}`@Client.register <lightbulb.client.Client.register>`
- {meth}`@Client.error_handler <lightbulb.client.Client.error_handler>`
- {meth}`@Client.task <lightbulb.client.Client.task>`
- {meth}`@Loader.command <lightbulb.loaders.Loader.command>` (due to it calling `Client.register` internally)
- {meth}`@Loader.listener <lightbulb.loaders.Loader.listener>`
- {meth}`@Loader.task <lightbulb.loaders.Loader.task>`

If you need to enable dependency injection on other functions, you can decorate it with
{meth}`@lightbulb.di.with_di <linkd.solver.with_di>` - from  then on, each time the function is called,
lightbulb will attempt to dependency inject suitable parameters.

:::{important}
For a parameter to be suitable for dependency injection, it needs to match the following rules:
- It **must** have a type annotation
- It has no default value, or a default value of exactly {const}`lightbulb.di.INJECTED <linkd.solver.INJECTED>`
- It **cannot** be positional-only, var-positional, or var-keyword (injected parameters are always passed using keywords)
:::

### Injecting Containers

When a container is active, it automatically registers itself as a dependency of the type {obj}`~linkd.containers.Container`.
Along with this, when you enter one of the Lightbulb-defined contexts, a special type is registered which is the container
for that specific context. These are as follows:

- {obj}`lightbulb.di.DefaultContainer <linkd.solver.DefaultContainer>`
- {obj}`lightbulb.di.CommandContainer <lightbulb.di.CommandContainer>`
- {obj}`lightbulb.di.AutocompleteContainer <lightbulb.di.AutocompleteContainer>`
- {obj}`lightbulb.di.ListenerContainer <lightbulb.di.ListenerContainer>`
- {obj}`lightbulb.di.TaskContainer <lightbulb.di.TaskContainer>`

You can use any of these types within your injection-enabled functions in order to access them if you wish 
to register some ephemeral dependencies to them.

When using {obj}`~linkd.containers.Container` as the type hint, the passed value will be the most-recently
activated container for the current context. I.e. within a command it would return the same value as the type hint
{obj}`~lightbulb.di.CommandContainer`.

### Example

Simple example using an `aiohttp.ClientSession`:

```python
import aiohttp
import hikari
import lightbulb

bot = hikari.GatewayBot(...)
client = lightbulb.client_from_app(bot)
# Register the dependency - as seen before
client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_factory(
    aiohttp.ClientSession, 
    lambda: aiohttp.ClientSession()
)


class ExampleCommand(lightbulb.SlashCommand, name="example", description="example"):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, cs: aiohttp.ClientSession):
        # The 'cs' parameter will be injected upon the command being called
        ...
```

---

(cleanup)=
## Cleanup

Some dependencies need to be cleaned up once the bot stops. Lightbulb allows you to do this by providing a teardown
callback when registering your dependencies. This callback can only take a single argument, which will be
the dependency that is being torn-down. These teardown methods will be called for all dependencies once the
container for that dependency is closed.

For flow-specific dependencies, the teardown will be run when that flow is finished. For example, a command-only
dependency will be cleaned up once the execution of that command - including any hooks and error handlers - has
completed.

For any dependencies added to the `DEFAULT` context, in order for the teardown callbacks to be called you **must**
close the Lightbulb client by calling the method {meth}`Client.stop() <lightbulb.client.Client.stop>`. It is 
recommended that you hook into the Hikari bot's lifecycle in order to do this.

:::{tab} GatewayBot
```python
import hikari
import lightbulb

bot = hikari.GatewayBot(...)
client = lightbulb.client_from_app(bot)
# Register Client.stop to be called when the bot is stopped
bot.subscribe(hikari.StoppingEvent, client.stop)
```
:::
:::{tab} RESTBot
```python
import hikari
import lightbulb

bot = hikari.RESTBot(...)
client = lightbulb.client_from_app(bot)
# Register Client.stop to be called when the bot is stopped
bot.add_shutdown_callback(client.stop)
```
:::

---

(union-dependencies)=
## Union and Optional Dependencies

When injecting dependencies into either a dependency factory method, or a dependency injection enabled function - Lightbulb
supports specifying unions in order to allow for fallbacks when one or more dependencies are not registered.

For example, if you want to use the same factory method for both command and autocomplete invocations, you could do
the following:

```python
async def dependency_factory(ctx: lightbulb.Context | lightbulb.AutocompleteContext) -> Foo:
    ...
```

In this case, Lightbulb would recognise when `Context` isn't available in the container and would provide `AutocompleteContext`
instead.

Similarly, the special case {obj}`typing.Optional` (`typing.Optional[Foo]` or `Foo | None`) is supported - when the
parameter is needed to be injected, Lightbulb will check if the dependency `Foo` exists in the container, if not,
the parameter value will be `None` instead of the created dependency.

### Modifying Resolution Behaviour

The default behaviour for resolving union dependencies works as follows:

- Check dependencies in the order specified in the union
- For each dependency, check if it is registered to the container (or a parent container)
- If registered, return that dependency
- Otherwise, check the next dependency in the sequence

Lightbulb provides some "meta annotations" that allow you to slightly alter this behaviour. For example, you could
change it so that if creating one of the dependencies fails (even if it is registered), then Lightbulb will try to
fall back to the next dependency in the sequence.

```python
from lightbulb.di import Try

async def dependency_factory(foo: Try[Bar] | Baz) -> Bork:
    ...
```

In the above example, `Try[]` acts as a modifier that tells the injection system to always attempt to create
the enclosed dependency, and fall back if creation fails. If `Try[]` was not included, then an error would
be raised if creation of the `Bar` dependency failed - and the method would not be called.

:::{note}
The absense of a "meta annotation" is functionally identical to the dependency type being enclosed within an `If[]`.

E.g. the following two examples will function the same way
```python
async def dependency_factory(foo: Bar) -> Baz:
    ...
```
```python
from lightbulb.di import If

async def dependency_factory(foo: If[Bar]) -> Baz:
    ...
```
:::

---

## Examples

### Basic

A basic worked example with a working command you should be able to drop straight into your own bot.

:::{dropdown} Code
```python
import aiohttp
import hikari
import lightbulb

# Returns a random 200x200 image when fetched with a GET request
RANDOM_IMAGE_URL = "https://picsum.photos/200"

# Initialise the bot and Lightbulb client
bot = hikari.GatewayBot("your token")
client = lightbulb.client_from_app(bot)
# Hook client into bot's lifecycle
bot.subscribe(hikari.StartingEvent, client.start)
bot.subscribe(hikari.StoppingEvent, client.stop)

# Define the dependency teardown method
async def close_client_session(cs: aiohttp.ClientSession) -> None:
    await cs.close()

# Register the dependency we want to use later
client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_factory(
    aiohttp.ClientSession, 
    lambda: aiohttp.ClientSession(),
    teardown=close_client_session,
)


@client.register
class RandomImage(
    lightbulb.SlashCommand,
    name="random-image",
    description="Generates a random image using the picsum API"
):
    # The 'lightbulb.invoke` decorator enables dependency injection on the function, so we
    # do not need to include the 'lightbulb.di.with_di' decorator here
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
:::

### Flow-scoped Dependencies

A more advanced example implementing a basic currency system with wallets stored in Redis. We use a command-scoped
dependency to fetch and save the wallet changes automatically within each command.

:::{dropdown} Code
```python
import os

import hikari
import lightbulb
import redis.asyncio as redis


class Wallet:
    def __init__(self, r: redis.Redis, user_id: str, balance: int = 0) -> None:
        self.r = r
        self.user_id = user_id
        self.balance = balance

    # We are going to call this in our teardown function for the Wallet dependency
    # so that it gets saved back to Redis automatically
    async def save(self) -> None:
        await self.r.set(self.user_id, str(self.balance))


# Initialise the bot and Lightbulb client
bot = hikari.GatewayBot("your token")
client = lightbulb.client_from_app(bot)
# Hook client into bot's lifecycle
bot.subscribe(hikari.StartingEvent, client.start)
bot.subscribe(hikari.StoppingEvent, client.stop)

# Register the redis client as a dependency
client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_factory(
    redis.Redis,
    lambda: redis.from_url(os.environ["REDIS_URL"]),
    teardown=redis.Redis.aclose
)

# Define the factory for creating the Wallet instance
async def get_wallet(r: redis.Redis, ctx: lightbulb.Context) -> Wallet:
    balance: bytes | None = await r.get(user_id := str(ctx.user.id))
    return Wallet(r, user_id, 0 if balance is None else int(balance.decode("utf-8")))

# Register the wallet as a dependency for the COMMAND injection context
client.di.registry_for(lightbulb.di.Contexts.COMMAND).register_factory(
    Wallet,
    get_wallet,
    teardown=lambda w: w.save()
)


@client.register
class Balance(
    lightbulb.SlashCommand,
    name="balance",
    description="Get your current balance",
):
    # The 'lightbulb.invoke` decorator enables dependency injection on the function, so we
    # do not need to include the 'lightbulb.di.with_di' decorator here
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, wallet: Wallet) -> None:
        # The injected value for 'wallet' will be the wallet for the person who invoked the command
        await ctx.respond(f"Your current balance is `{wallet.balance}`.")


# Run the bot
if __name__ == "__main__":
    bot.run()
```
:::

---

## Disabling DI

If you wish to run your application with no dependency injection, Lightbulb allows you
to disable the entire system by setting the environment variable `LINKD_DI_DISABLED` to `true`.

This will prevent decorators from wrapping functions to enable DI and will prevent parameter processing
from attempting to resolve injectable parameters.

---

## A Note on `TYPE_CHECKING`

Given that the DI system relies heavily on type-hints, you need to be careful when using:

```python
from __future__ import annotations
```

Type hints within files containing this import will be evaluated as strings and passed a single context value `lightbulb`.
This means that you **cannot** have any typehints using an alias to `lightbulb` (within the {obj}`~typing.TYPE_CHECKING` block)
such as the below:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import lightbulb as lb  # !!!


# An exception will be thrown when attempting to parse this signature to resolve the dependencies
async def your_method(container: lb.di.Container) -> None:
    ...
```

Make sure that if you are using a lightbulb typehint within a file like this that it is **always** imported explicitly
as `lightbulb`.
