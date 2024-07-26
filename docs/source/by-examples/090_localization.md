# Localization

Application commands can be localized, which will cause them to use localized names and descriptions depending on 
the client's selected language. Localization is available for names and descriptions of commands, subcommands, 
and options, as well as the names of choices.

Not all available locales are required, nor do different fields within a command need to support the same set of 
locales. If a locale is not present in a localizations dictionary for a field, users in that locale will see 
the default value for that field. It's not necessary to fill out all locales with the default value. Any 
localized values that are identical to the default will be ignored.

:::{seealso}
Discord [documentation](https://discord.com/developers/docs/interactions/application-commands#localization)
:::

---

## Implementation

To implement localization within your bot, you must first supply a localization provider when creating the Client.
This provider will be used to resolve all localizations for the previously mentioned fields. This resolution
step **only** occurs when the bot is started due to them being needed while syncing commands with Discord.

A localization provider is any callable (synchronous or asynchronous) that when called with a localization key, returns
the dictionary mapping locales to the localized strings for that key.

Lightbulb provides two localization providers by default. The more basic one 
{obj}`~lightbulb.localization.DictLocalizationProvider` simply provides localizations from the dict it is given
upon instantiation. The other included provider - {obj}`~lightbulb.localization.GnuLocalizationProvider` - provides
localizations from a gettext-compatible file path using `.po` or `.mo` files.

Once you have set up a localization provider, you can simply pass `localize=True` to any items that you wish to localize
and Lightbulb will resolve the correct localizations from the name (and description) keys.

---

## Setting Default Locale

The default locale defines what localizations the client will use as the default when creating commands. You can
change this by passing a different locale to the `default_locale` kwarg when creating the client. This defaults
to `EN_US`.

---

## DictLocalizationProvider

Usage of this provider is extremely simple. A complete example is shown below.

```python
import hikari
import lightbulb

bot = hikari.GatewayBot(...)

localization_provider = lightbulb.DictLocalizationProvider({
    hikari.Locale.EN_US: {
        "commands.echo.name": "echo",
        "commands.echo.description": "repeats the given text",
        "commands.echo.options.text.name": "text",
        "commands.echo.options.text.description": "text to repeat"
    },
    hikari.Locale.ES_ES: {
        "commands.echo.name": "eco",
        "commands.echo.description": "repite el texto dado",
        "commands.echo.options.text.name": "texto",
        "commands.echo.options.text.description": "texto a repetir"
    }
})
client = lightbulb.client_from_app(bot, localization_provider=localization_provider)
bot.subscribe(hikari.StartingEvent, client.start)


@client.register
class Echo(
    lightbulb.SlashCommand,
    # The below values are used as the keys from which to resolve the correct localizations from
    name="commands.echo.name",
    description="commands.echo.description",
    # This command should be localized
    localize=True,
):
    text = lightbulb.string(
        "commands.echo.options.text.name",
        "commands.echo.options.text.description",
        localize=True,
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(self.text)


bot.run()
```

---

## GnuLocalizationProvider

This provider is more complex and relies on the correct file structure being present in order to work correctly. With
the default values, your project structure could look something like this.

```
bot.py
translations/
├── en-US/
│   └── LC_MESSAGES/
│       └── commands.po
└── es-ES/
    └── LC_MESSAGES/
        └── commands.po
```

The expected path can be modified by passing different values to the `directory`, `category`, and `filename` arguments
when instantiating the provider.

:::{warning}
This provider **does not** support the following features:
- Plurals
- `.pot` files
- Contexts

You should use only the most barebone `.po` files possible. If you need more features for other functionality you
should use a differently named file.
:::

Implementing the previous example again but using this localization provider instead would look like this. Note that
in this example we are using the same project structure mentioned before.

:::{tab} bot.py
```python
import hikari
import lightbulb

bot = hikari.GatewayBot(...)
client = lightbulb.client_from_app(bot, localization_provider=lightbulb.GnuLocalizationProvider("commands.po"))
bot.subscribe(hikari.StartingEvent, client.start)


@client.register
class Echo(
    lightbulb.SlashCommand,
    # The below values are used as the keys from which to resolve the correct localizations from
    name="commands.echo.name",
    description="commands.echo.description",
    # This command should be localized
    localize=True,
):
    text = lightbulb.string(
        "commands.echo.options.text.name",
        "commands.echo.options.text.description",
        localize=True,
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(self.text)


bot.run()
```
:::

:::{tab} en-US
```po
msgid ""
msgstr ""
"Project-Id-Version: Lightbulb Demo\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2024-07-02 15:25+0000\n"
"PO-Revision-Date: 2024-07-02 15:25+0000\n"
"Last-Translator: \n"
"Language-Team: English\n"
"Language: en-US\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"

msgid "commands.echo.name"
msgstr "echo"

msgid "commands.echo.description"
msgstr "repeats the given text"

msgid "commands.echo.options.text.name"
msgstr "text"

msgid "commands.echo.options.text.description"
msgstr "text to repeat"
```
:::

:::{tab} es-ES
```po
msgid ""
msgstr ""
"Project-Id-Version: Lightbulb Demo\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2024-07-02 15:25+0000\n"
"PO-Revision-Date: 2024-07-02 15:25+0000\n"
"Last-Translator: \n"
"Language-Team: Spanish\n"
"Language: es-ES\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"

msgid "commands.echo.name"
msgstr "eco"

msgid "commands.echo.description"
msgstr "repite el texto dado"

msgid "commands.echo.options.text.name"
msgstr "texto"

msgid "commands.echo.options.text.description"
msgstr "texto a repetir"
```
:::
