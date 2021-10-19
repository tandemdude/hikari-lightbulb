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
__all__ = ["Check"]

import typing as t

from lightbulb_v2 import context as context_

T = t.TypeVar("T")
_CallbackT = t.Callable[[context_.base.Context], t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]]


class Check:
    __slots__ = ("prefix_callback", "slash_callback", "message_callback", "user_callback", "add_to_object_hook")

    def __init__(
            self,
            p_callback: _CallbackT,
            s_callback: t.Optional[_CallbackT] = None,
            m_callback: t.Optional[_CallbackT] = None,
            u_callback: t.Optional[_CallbackT] = None,
            add_hook: t.Optional[t.Callable[[T], T]] = None
    ) -> None:
        self.prefix_callback = p_callback
        self.slash_callback = s_callback or p_callback
        self.message_callback = m_callback or p_callback
        self.user_callback = u_callback or p_callback
        self.add_to_object_hook = add_hook or (lambda o: o)

    def __call__(self, context: context_.base.Context) -> t.Union[bool, t.Coroutine[t.Any, t.Any, bool]]:
        if isinstance(context, context_.prefix.PrefixContext):
            return self.prefix_callback(context)
        elif isinstance(context, context_.slash.SlashContext):
            return self.slash_callback(context)
        elif isinstance(context, context_.message.MessageContext):
            return self.message_callback(context)
        elif isinstance(context, context_.user.UserContext):
            return self.user_callback(context)
        return True
