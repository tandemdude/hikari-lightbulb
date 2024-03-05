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

LocalizationMappingT: t.TypeAlias = t.Mapping[hikari.Locale, str]
LocalizationProviderT: t.TypeAlias = t.Callable[[str], LocalizationMappingT]


def _(string: str) -> str:
    """
    Utility function to fool ``xgettext`` into generating a correct ``.po`` file
    from command and option localization keys.

    Just returns the value that is passed in with no processing.
    """
    return string


def localization_unsupported(_: str) -> t.NoReturn:
    raise exceptions.LocalizationFailedException("no localization provider available - localization is not supported")


@dataclasses.dataclass(slots=True, frozen=True)
class DictLocalizationProvider:
    localizations: t.Mapping[hikari.Locale, t.Mapping[str, str]]

    def __call__(self, key: str) -> LocalizationMappingT:
        out: t.Dict[hikari.Locale, str] = {}
        for locale, translations in self.localizations.items():
            if key in translations:
                out[locale] = translations[key]

        return out


@dataclasses.dataclass(slots=True)
class GnuLocalizationProvider:
    filename: str
    directory: str = "translations"
    category: str = "LC_MESSAGES"

    _dict_provider: DictLocalizationProvider = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        try:
            import polib
        except ImportError as e:
            raise ImportError(f"'hikari-lightbulb[localization]' is required to use {self.__class__.__name__!r}") from e

        if not self.filename.endswith(".po") and not self.filename.endswith(".mo"):
            raise ValueError("'filename' - file must be of type '.po' or '.mo'")

        localizations: t.Dict[hikari.Locale, t.Dict[str, str]] = collections.defaultdict(dict)

        for directory in pathlib.Path(self.directory).iterdir():
            if not directory.is_dir():
                continue

            if directory.name not in hikari.Locale:
                continue

            locale = hikari.Locale(directory.name)
            translations_file = directory / self.category / self.filename
            if not translations_file.is_file():
                continue

            parsed: t.Union[polib.POFile, polib.MOFile] = (
                polib.pofile(translations_file.as_posix())
                if translations_file.name.endswith(".po")
                else polib.mofile(translations_file.as_posix())
            )

            obsolete = parsed.obsolete_entries()
            entries = [entry for entry in parsed if entry not in obsolete]
            for entry in entries:
                localizations[locale][entry.msgid] = entry.msgstr

        self._dict_provider = DictLocalizationProvider(localizations)

    def __call__(self, key: str) -> LocalizationMappingT:
        return self._dict_provider(key)
