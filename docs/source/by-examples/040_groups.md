# Groups

Command groups allow you to organize multiple commands into a single tree-like structure. You can have up to
two levels of grouping.

An example group structure could be the following:

```
group
├── subgroup
│   ├── foo
│   └── bar
└── baz
```

This would create the following commands for the user:
- `/group subgroup foo`
- `/group subgroup bar`
- `/group baz`

---

## Creating a Group

Creating a group is as easy as creating an instance of the `Group` class. Like slash commands, groups **must** have
a name and description. Other parameters can be seen in the documentation.

```python
group = lightbulb.Group("group", "a command group")
```

Given that subgroups must be linked to a command group, the method `Group.subgroup()` must be used to create one.
Subgroups must also have a name and description.

```python
subgroup = group.subgroup("subgroup", "a command subgroup")
```

---

## Adding Commands

Registering a command to a group or subgroup is very similar to registering it to the Lightbulb client - using
the `Group.register` (or `SubGroup.register`) decorator.

```python
group = lightbulb.Group(...)


@group.register
class YourCommand(
    lightbulb.SlashCommand,
    ...
):
    ...
```

:::{important}
Only `SlashCommand`s can be added to groups - context menu commands cannot and will error.
:::

---

## Registering Groups

After you have created your group and added your commands, you will need to register the group with the `Client` so
that they can be used by your users. Like normal commands, this is done using the `Client.register` method.

```python
group = lightbulb.Group(...)


@group.register
class YourCommand(
    lightbulb.SlashCommand,
    ...
):
    ...


# Register the group globally
client.register(group)
# If you want to limit the command to specific guilds
client.register(group, guilds=[...])
```

After doing this - and starting the client - the command group's subcommands should appear within Discord and be usable.
