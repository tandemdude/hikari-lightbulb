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

__all__ = ["Localization", "LocalizationManager"]

import importlib
import inspect
import logging
import pathlib
import typing as t

if t.TYPE_CHECKING:
    import types

    import hikari

LOGGER = logging.getLogger("lightbulb.localization")


class Localization:
    __slots__ = ("_locale", "_translations")

    def __init__(self, locale: hikari.Locale, translations: t.Mapping[str, str]) -> None:
        self._locale = locale
        self._translations = translations

    def get(self, key: str) -> t.Optional[str]:
        return self._translations.get(key, None)

    def merge(self, other: Localization) -> Localization:
        new: t.Dict[str, str] = {}
        new.update(self._translations)

        conflicts: t.List[str] = []
        for key, value in other._translations:
            if key in new:
                conflicts.append(key)
                continue

            new[key] = value

        if conflicts:
            LOGGER.warning("ignoring conflicting keys found while merging localizations - %r", conflicts)

        return Localization(self._locale, new)


class LocalizationManager:
    __slots__ = ("_default_locale", "_localizations")

    def __init__(self, default_locale: hikari.Locale) -> None:
        self._default_locale = default_locale
        self._localizations: t.Dict[hikari.Locale, Localization] = {}

    def get_default(self, key: str) -> t.Optional[str]:
        localization = self._localizations.get(self._default_locale)
        if localization is None:
            return None

        return localization.get(key)

    def get_all(self, key: str) -> t.Dict[hikari.Locale, str]:
        out: t.Dict[hikari.Locale, str] = {}

        for locale, localization in self._localizations.items():
            if (localized := localization.get(key)) is not None:
                out[locale] = localized

        return out

    def get_non_default(self, key: str) -> t.Dict[hikari.Locale, str]:
        out = self.get_all(key)
        out.pop(self._default_locale, None)
        return out

    def register(self, localization: Localization) -> None:
        if localization._locale in self._localizations:
            LOGGER.debug("duplicate localization found for locale %r - merging with existing", localization._locale)
            localization = self._localizations[localization._locale].merge(localization)

        self._localizations[localization._locale] = localization

    def register_from_module(self, module: types.ModuleType) -> None:
        to_register: t.List[Localization] = []

        for item in dir(module):
            value = getattr(module, item, None)

            if not isinstance(value, Localization):
                continue

            to_register.append(value)

        LOGGER.debug("registering %s localization(s) found in module %r", len(to_register), module.__name__)
        for found in to_register:
            self.register(found)

    def register_from_package(self, pkg: types.ModuleType) -> None:
        init_file_path = pathlib.Path(inspect.getfile(pkg))
        if init_file_path.name != "__init__.py":
            raise ValueError("the given module is not a package")

        package_import_name = pkg.__name__

        for item in init_file_path.parent.iterdir():
            if item.is_dir():
                # TODO
                continue

            if item.name.startswith("__") or not item.name.endswith(".py"):
                continue

            try:
                module = importlib.import_module(f"{package_import_name}.{item.name[:-3]}")
            except Exception as e:
                LOGGER.warning(
                    "failed to import module %r - skipping",
                    f"{package_import_name}.{item.name[:-3]}",
                    exc_info=(type(e), e, e.__traceback__),
                )
                continue

            self.register_from_module(module)
