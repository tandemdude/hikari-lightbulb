# Preface

Whether you are a new developer using Lightbulb, or a returning developer experienced using V2 you are likely to
encounter some quirks with the library or have some ideas that you aren't quite sure how to implement.

This series of pages aims to introduce you slowly to the main ideas behind the new version of Lightbulb
and how to use them to their full potential in order to develop the Discord bot of your dreams.

---

## New developers

In the following examples I expect you to be familiar with Python's syntax, especially class definitions and
async Python. You should probably read into the basics if you have not already - there are many great resources
on the internet that will explain them to you much better than this documentation can.

---

## Returning developers

Much has changed since the release of V2 - although almost everything about the library has changed, you will
likely find similar themes that you are used to with the experience you have gained with the library previously.

For additional help with migrating existing code you should view the migration guide which is aimed to suggest
1-to-1 replacements for common patterns that you have used before (although some functionality *may* have to be
implemented yourself).

:::{note}
As of version 3, prefix command support has been completely removed. If you still wish to support prefix commands
you will have to create a listener for Hikari's `MessageCreateEvent` and process and parse the messages manually.

This may be more inconvenient for you but it allowed me to greatly simplify the internals and developer-facing
API for a better experience (no more long decorator stacks).
:::

Most of all, do not be afraid to ask for help either in the Hikari [Discord server](https://discord.gg/hikari) or by 
creating a discussion on the [repository](https://github.com/tandemdude/hikari-lightbulb).

---

## Project Setup

First of all, create an application (if you haven't already) on the [discord developer portal](https://discord.com/developers/docs/quick-start/getting-started#step-1-creating-an-app).
Their guide explains it far better than I can.

A Lightbulb [project template](https://github.com/tandemdude/hikari-lightbulb-bot-template) exists for your convenience
and can be used to initialise your project with a known-good structure and basic working implementation if you wish.

---

### First Steps

To get Lightbulb working in your project, you first need to create a Hikari bot object. Lightbulb supports both
[`hikari.GatewayBot`](https://docs.hikari-py.dev/en/latest/#gatewaybot) and [`hikari.RESTBot`](https://docs.hikari-py.dev/en/latest/#gatewaybot).
The steps for setting up both to work with Lightbulb are the same:

:::{tab} GatewayBot
```python
import hikari
import lightbulb

bot = hikari.GatewayBot(
    token="...",
)
# Set up the lightbulb client
client = lightbulb.client_from_app(bot)
```
:::

:::{tab} RESTBot
```python
import hikari
import lightbulb

bot = hikari.RESTBot(
    token="...",
    token_type="...",
    public_key="...",
)
# Set up the lightbulb client
client = lightbulb.client_from_app(bot)
```
:::

The Lightbulb client must then be started in order to sync commands with discord and begin processing interactions:

:::{tab} GatewayBot
```python
bot.subscribe(hikari.StartingEvent, client.start)
```
:::

:::{tab} RESTBot
```python
bot.add_startup_callback(client.start)
```
:::

You are now ready to write your first command.
