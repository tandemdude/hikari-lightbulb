# Extensions

Extensions are used to assist in splitting up your project into multiple files. A Python file is considered
an extension if it declares one or more variables that are instances of `lightbulb.Loader`s. Upon loading
an extension into the client, it will search for any loaders and apply them - adding commands, listeners, etc.

---

## Loaders

A loader is the client's 'entry point' for an extension.

In a new Python file, you can create a loader like so:
```python
import lightbulb

loader = lightbulb.Loader()
```

This file is now an 'extension'. Next you probably want to add some functionality that can be added when the extension
is loaded. Currently, loaders support commands, listeners and error handlers natively - but support can easily be added
for loading of other items.

### Commands

```python
@loader.command
class YourCommand(
    ...
):
    ...
```

### Listeners

```python
@loader.listener(...)
async def your_listener(...) -> None:
    ...
```

### Error Handlers

```python
@loader.error_handler
async def your_error_handler(...) -> bool:
    ...
```

:::{tip}
Other items can be linked to loaders by implementing a custom `lightbulb.Loadable` that enables the desired
behaviour. This loadable can be added to a given loader using the `Loader.add()` method.
:::

---

## Loading Extensions

Lightbulb provides two methods to help with loading extensions into the client.
These are `Client.load_extensions()` - loading one or more extensions using the import path, and
`Client.load_extenions_from_package()` - loading multiple extensions using an imported package that contains the
extension files.

:::{warning}
Unlike V2, the load extensions methods are now **asynchronous**. This means that you will need an event loop
available in order to load them. It is recommended that you do this during a startup listener. It is important
that you load any extensions **before** starting the client, otherwise any commands may not be synced with Discord.
:::


Example file structure:
```
extensions/
├── __init__.py
├── echo.py
└── ping.py
```

### `load_extensions()`

This method takes the **import path** for any extensions you want to load. Given the example file structure,
this would look like the following:

```python
await client.load_extensions("extensions.echo", "extensions.ping")
```

### `load_extensions_from_package()`

This method takes an **imported package** containing the extensions you want to load. Given the example file
structure, this would look like the following:

```python
import extensions

await client.load_extensions_from_package(extensions)
```

If the `recursive` flag is set to `True`, this method will also search through subpackages for extensions. This
defaults to `False`.

---

## Example Usage

```python
import hikari
import lightbulb

bot = hikari.GatewayBot(...)
client = lightbulb.client_from_app(bot)


@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    # Load any extensions
    await client.load_extensions("extensions.foo", "extensions.bar", "extensions.baz")
    # Start the bot - make sure commands are synced properly
    await client.start()


bot.run()
```
