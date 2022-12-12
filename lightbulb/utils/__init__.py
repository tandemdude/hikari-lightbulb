# -*- coding: utf-8 -*-
# Copyright © tandemdude 2020-present
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

__all__ = [
    "ButtonNavigator",
    "ComponentButton",
    "DataStore",
    "EmbedPaginator",
    "Paginator",
    "ReactionButton",
    "ReactionNavigator",
    "StringPaginator",
    "find",
    "first_page",
    "get",
    "last_page",
    "next_page",
    "permissions_for",
    "permissions_in",
    "prev_page",
    "stop",
    "build_invite_url",
    "data_store",
    "nav",
    "pag",
    "permissions",
    "search",
]

import typing as t
from urllib import parse

import hikari

from lightbulb.utils import data_store
from lightbulb.utils import nav
from lightbulb.utils import pag
from lightbulb.utils import permissions
from lightbulb.utils import search
from lightbulb.utils.data_store import *
from lightbulb.utils.nav import *
from lightbulb.utils.pag import *
from lightbulb.utils.permissions import *
from lightbulb.utils.search import *

if t.TYPE_CHECKING:
    from lightbulb import app as app_


def build_invite_url(
    app: app_.BotApp,
    permissions: hikari.Permissions = hikari.Permissions.NONE,
    allow_commands: bool = False,
) -> str:
    """
    Build an invite link for the given :obj:`~.app.BotApp` with the given permissions and scopes. This
    adds the ``bot`` scope to the URL by default.

    Args:
        app (:obj:`~.app.BotApp`): :obj:`~.app.BotApp` instance to create the invite link for.
        permissions (:obj:`hikari.Permissions`): Permissions to add to the invite link. Defaults to
            :obj:`hikari.Permissions.NONE`.
        allow_commands (:obj:`bool`): Whether to add the `applications.commands` scope to the invite link. Defaults
            to ``False``.

    Returns:
        :obj:`str`: Created invite link.

    .. versionadded:: 2.2.0
    """
    if app.application is None:
        raise ValueError("Cannot build invite url when 'app.application' is None")

    raw_scopes = {"bot"}
    if allow_commands:
        raw_scopes.add("applications.commands")

    scopes = " ".join(raw_scopes)
    return "https://discord.com/api/oauth2/authorize?" + parse.urlencode(
        {"client_id": app.application.id, "permissions": int(permissions), "scope": scopes}
    )
