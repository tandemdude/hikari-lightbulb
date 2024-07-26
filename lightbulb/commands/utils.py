# -*- coding: utf-8 -*-
# api_reference_gen::ignore
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

__all__ = ["localize_value", "localize_name_and_description"]

import typing as t

from lightbulb import exceptions
from lightbulb import utils

if t.TYPE_CHECKING:
    import hikari

    from lightbulb import localization


async def localize_value(
    value: str, default_locale: hikari.Locale, localization_provider: localization.LocalizationProvider
) -> tuple[str, t.Mapping[hikari.Locale, str]]:
    """
    Get the value, and localized values for the given string, using the provided localization provider.

    Args:
        value: The string to get the localized values for.
        default_locale: The default locale to use.
        localization_provider: The localization provider to use.

    Returns:
        The string localized to the default locale, and a dictionary containing the localized values for all
        the remaining locales.
    """
    localizations: t.Mapping[hikari.Locale, str] = await utils.maybe_await(localization_provider(value))
    localized_value = localizations.get(default_locale, None)
    if localized_value is None:
        raise exceptions.LocalizationFailedException(f"failed to resolve key {value!r} for default locale")

    return localized_value, localizations


async def localize_name_and_description(
    name: str,
    description: str | None,
    default_locale: hikari.Locale,
    localization_provider: localization.LocalizationProvider,
) -> tuple[str, str, t.Mapping[hikari.Locale, str], t.Mapping[hikari.Locale, str]]:
    """
    Helper method to resolve the localizations for the name and description of a command
    using the given localization provider.

    Args:
        name: The command's name
        description: The command's description
        default_locale: The default locale to use for the command.
        localization_provider: The localization provider
            to use to get the available localizations for the command.

    Returns:
        Tuple containing the resolved name, description and localizations for the name and description.
    """
    localized_name, name_localizations = await localize_value(name, default_locale, localization_provider)

    localized_description = ""
    description_localizations: t.Mapping[hikari.Locale, str] = {}
    if description is not None:
        localized_description, description_localizations = await localize_value(
            description, default_locale, localization_provider
        )

    return localized_name, localized_description, name_localizations, description_localizations
