# Autocomplete

Autocomplete is a Discord feature that allows your bot to suggest values for an option dynamically based on the content
already entered by the user within the option being autocompleted, as well as other options already filled in.

:::{note}
Only options of type `string`, `integer`, or `number` can be autocompleted.
:::

Lightbulb implements autocomplete by allowing you to specify an 'autocomplete callback' function that will be
called for every autocomplete interaction sent when that option is focused.

---

## Callback Specification

An autocomplete callback is an **asynchronous** function that takes an instance of 
{obj}`~lightbulb.context.AutocompleteContext` as its first argument - any return value will be discarded. Further
arguments will be dependency injected.

Within an autocomplete callback, you are required to call the {meth}`~lightbulb.context.AutocompleteContext.respond`
method **exactly once**. This is what actually submits the autocompletion suggestions to Discord. For details
about the acceptable values you can pass to `respond()`, see the method's documentation.

---

## Implementation

To make an option autocomplete-able, you simply pass the callback function into the `autocomplete` argument
of the respective option function.

For example using a `string` option:

```python
class Command(
    lightbulb.SlashCommand,
    ...
):
    option = lightbulb.string(..., autocomplete=your_autocomplete_callback)

    ...
```

---

## Full Example Command

The below example is a command with a single autocomplete-able string option that simply recommends 10 random
strings that are prefixed with the characters the user has already input.

```python
import string
import random

import lightbulb

ALL_CHARS = string.ascii_letters + string.digits


async def autocomplete_callback(ctx: lightbulb.AutocompleteContext[str]) -> None:
    current_value: str = ctx.focused.value or ""
    values_to_recommend = [
        current_value + "".join(random.choices(ALL_CHARS, k=5)) for _ in range(10)
    ]
    await ctx.respond(values_to_recommend)


class RandomCharacters(
    lightbulb.SlashCommand,
    name="randomchars",
    description="autocomplete demo command"
):
    text = lightbulb.string("text", "autocompleted option", autocomplete=autocomplete_callback)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond(self.text)
```
