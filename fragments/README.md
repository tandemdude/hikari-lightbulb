# Changelog Fragments

This directory contains the fragments which will be used by towncrier to build the changelog for the next release
version.

If you are making a change worth mentioning you should create a fragment in this directory containing a short description
of the change. The fragment filename should be in the form `<pr number>.<type>.md`

## Valid Fragment Types

- `breaking` - a breaking change
- `removal` - removal of a feature
- `deprecation` - a deprecation
- `feature` - addition of a feature
- `bugfix` - a bugfix
- `doc` - notable changes to the documentation
- `misc` - miscellaneous changes that do not better fit another type

## Example

`123.feature.md`
```md
Add `foo` method to `Bar` class.
```
