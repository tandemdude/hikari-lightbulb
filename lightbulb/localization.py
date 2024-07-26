# -*- coding: utf-8 -*-
# Copyright (c) 2023-present tandemdude
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

__all__ = ["localization_unsupported", "DictLocalizationProvider", "GnuLocalizationProvider"]

import collections
import dataclasses
import pathlib
import typing as t

import hikari

from lightbulb import exceptions
from lightbulb.internal import types

LocalizationMapping: t.TypeAlias = t.Mapping[hikari.Locale, str]
LocalizationProvider: t.TypeAlias = t.Callable[[str], types.MaybeAwaitable[LocalizationMapping]]


def localization_unsupported(_: str) -> t.NoReturn:
    """
    Default localization provider. Functions to disable the ability to localize commands and options. If
    you want to use localized commands in your application you should specify a different built-in or custom
    localization provider.

    Raises:
        :obj:`~lightbulb.exceptions.LocalizationFailedException`: Whenever called. This means that
            when the client attempts to register commands with discord it will cause this error to be thrown if
            any of the commands (or options) are marked as requiring localization.
    """
    raise exceptions.LocalizationFailedException("no localization provider available - localization is not supported")


@dataclasses.dataclass(slots=True, frozen=True)
class DictLocalizationProvider:
    """Basic localization provider that supplies localizations from a single dictionary."""

    localizations: t.Mapping[hikari.Locale, t.Mapping[str, str]]
    """Mapping containing the localizations that can be provided."""

    def __call__(self, key: str) -> LocalizationMapping:
        out: dict[hikari.Locale, str] = {}
        for locale, translations in self.localizations.items():
            if key in translations:
                out[locale] = translations[key]

        return out


@dataclasses.dataclass(slots=True)
class GnuLocalizationProvider:
    """
    Localization provider that parses localizations from gnu gettext compatible '.po' or '.mo' file paths. This
    provider expects localizations to be available from the file structure expected by gettext.

    I.e. ``{directory}/{locale}/{category}/{file}.[po|mo]`` (``translations/en-GB/LC_MESSAGES/commands.po``)
    """

    filename: str
    """The name of the file containing command translations."""
    directory: str = "translations"
    """The base directory where the locale directories can be found."""
    category: str = "LC_MESSAGES"
    """The category that the translation file can be found in. Defaults to 'LC_MESSAGES'."""

    _dict_provider: DictLocalizationProvider = dataclasses.field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            import polib
        except ImportError as e:
            raise ImportError(f"'hikari-lightbulb[localization]' is required to use {self.__class__.__name__!r}") from e

        if not self.filename.endswith(".po") and not self.filename.endswith(".mo"):
            raise ValueError("'filename' - file must be of type '.po' or '.mo'")

        localizations: dict[hikari.Locale, dict[str, str]] = collections.defaultdict(dict)

        for directory in pathlib.Path(self.directory).iterdir():
            if not directory.is_dir():
                continue

            if directory.name not in hikari.Locale:
                continue

            locale = hikari.Locale(directory.name)
            translations_file = directory / self.category / self.filename
            if not translations_file.is_file():
                continue

            parsed: polib.POFile | polib.MOFile = (
                polib.pofile(translations_file.as_posix())
                if translations_file.name.endswith(".po")
                else polib.mofile(translations_file.as_posix())
            )

            obsolete = parsed.obsolete_entries()
            entries = [entry for entry in parsed if entry not in obsolete]
            for entry in entries:
                localizations[locale][entry.msgid] = entry.msgstr

        self._dict_provider = DictLocalizationProvider(localizations)

    def __call__(self, key: str) -> LocalizationMapping:
        return self._dict_provider(key)
