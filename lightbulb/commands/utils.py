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

__all__ = ["localize_name_and_description"]

import typing as t

from lightbulb import exceptions
from lightbulb.internal import utils

if t.TYPE_CHECKING:
    import hikari

    from lightbulb import localization


async def localize_name_and_description(
    name: str,
    description: str | None,
    default_locale: hikari.Locale,
    localization_provider: localization.LocalizationProviderT,
) -> tuple[str, str, t.Mapping[hikari.Locale, str], t.Mapping[hikari.Locale, str]]:
    name_localizations: t.Mapping[hikari.Locale, str] = await utils.maybe_await(localization_provider(name))
    localized_name: str | None = name_localizations.get(default_locale, None)
    if localized_name is None:
        raise exceptions.LocalizationFailedException(f"failed to resolve key {name!r} for default locale")

    description_localizations: t.Mapping[hikari.Locale, str] = (
        {} if description is None else (await utils.maybe_await(localization_provider(description)))
    )
    localized_description: str | None = (
        "" if description is None else description_localizations.get(default_locale, None)
    )

    if description is not None and localized_description is None:
        raise exceptions.LocalizationFailedException(f"failed to resolve key {description!r} for default locale")

    assert localized_description is not None
    return localized_name, localized_description, name_localizations, description_localizations
