# -*- coding: utf-8 -*-
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

__all__ = ["LocalizationMappingT", "localize_name_and_description"]

import typing as t

import hikari

from lightbulb import exceptions

if t.TYPE_CHECKING:
    from lightbulb.localization import localization

LocalizationMappingT: t.TypeAlias = t.Mapping[t.Union[hikari.Locale, str], str]


def localize_name_and_description(
    name: str, description: t.Optional[str], localization_manager: localization.LocalizationManager
) -> t.Tuple[str, str, LocalizationMappingT, LocalizationMappingT]:
    localized_name = localization_manager.get_default(name)
    if localized_name is None:
        raise exceptions.LocalizationFailedException(f"failed to resolve key {name!r} for default locale")

    localized_description = "" if description is None else localization_manager.get_default(description)

    if description is not None and localized_description is None:
        raise exceptions.LocalizationFailedException(f"failed to resolve key {description!r} for default locale")

    name_localizations = t.cast(LocalizationMappingT, localization_manager.get_non_default(name))
    description_localizations = t.cast(
        LocalizationMappingT, {} if description is None else localization_manager.get_non_default(description)
    )

    assert localized_description is not None
    return localized_name, localized_description, name_localizations, description_localizations
