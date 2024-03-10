# -*- coding: utf-8 -*-
# api_reference_gen::ignore
# Copyright © tandemdude 2023-present
#
# This file is part of Lightbulb.
#
# Lightbulb is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Lightbulb is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Lightbulb. If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

__all__ = ["localize_name_and_description"]

import typing as t

from lightbulb import exceptions

if t.TYPE_CHECKING:
    import hikari

    from lightbulb import localization


def localize_name_and_description(
    name: str,
    description: str | None,
    default_locale: hikari.Locale,
    localization_provider: localization.LocalizationProviderT,
) -> tuple[str, str, t.Mapping[hikari.Locale, str], t.Mapping[hikari.Locale, str]]:
    name_localizations: t.Mapping[hikari.Locale, str] = localization_provider(name)
    localized_name: str | None = name_localizations.get(default_locale, None)
    if localized_name is None:
        raise exceptions.LocalizationFailedException(f"failed to resolve key {name!r} for default locale")

    description_localizations: t.Mapping[hikari.Locale, str] = (
        {} if description is None else localization_provider(description)
    )
    localized_description: str | None = (
        "" if description is None else description_localizations.get(default_locale, None)
    )

    if description is not None and localized_description is None:
        raise exceptions.LocalizationFailedException(f"failed to resolve key {description!r} for default locale")

    assert localized_description is not None
    return localized_name, localized_description, name_localizations, description_localizations
