# Appendix

---

## Components and Modals

Lightbulb includes a component handler (and modal handler) that you can use to make processing component and modal
interactions easier than it otherwise would be using raw Hikari code. For a usage guide you should see the
documentation for the {obj}`components subpackage <lightbulb.components>`.

---

## Scheduled and Repeating Tasks

Lightbulb supports scheduled and repeating tasks through the ``@Client.task`` and ``@Loader.task`` decorators. This
allows you to run logic every set interval, schedule it for a specific time, or anything else using unique triggers.
For more on this as well as a usage guide, see the documentation for the {obj}`tasks module <lightbulb.tasks>`.

---

## Configuration

Lightbulb provides configuration parsing from ``yaml``/``toml``/``json`` files into Python objects using
``msgspec``, with environment variable substitution evaluation. For more on this, see the documentation for the
{obj}`config module<lightbulb.config>`.

---

## Feature Flags

Lightbulb includes some feature flags in the {obj}`features module<lightbulb.features>` which allow you to modify
various portions of the library's behaviour which may better suit your usage. Consider taking a look and enabling
some when creating the ``Client`` if you find them useful.
