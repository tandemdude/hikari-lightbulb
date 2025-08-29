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
"""
Feature flags that can be used to enable new or different Lightbulb behaviours.

Specify when creating your ``Client`` instance:

.. code-block:: python

    client = lightbulb.client_from_app(..., features=[...])


.. versionadded:: 3.2.0
"""

from __future__ import annotations

__all__ = ["COMMAND_INJECT_CONTEXT", "HOOK_INJECT_ALL_PARAMS", "Feature"]

import dataclasses


@dataclasses.dataclass(slots=True, frozen=True)
class Feature:
    name: str
    """The name of the feature."""

    requires_di_enabled: bool = dataclasses.field(default=False, kw_only=True, hash=False, compare=False)
    """Whether the experiment requires DI to be globally enabled."""


HOOK_INJECT_ALL_PARAMS = Feature("HOOK_DI_ALL_PARAMS", requires_di_enabled=True)
"""
Use dependency injection for ALL execution hook parameters, allowing any (or both) of the
previously-required ``ExecutionPipeline`` and ``Context`` parameters to be omitted. Potentially
useful if you never use the ``ExecutionPipeline`` parameter and would like slightly cleaner
function signatures.
"""

COMMAND_INJECT_CONTEXT = Feature("COMMAND_INJECT_CONTEXT", requires_di_enabled=True)
"""
Use dependency injection for the ``Context`` parameter of command invoke methods. Could
be useful if you want to provide your own subclass with extra features, without having
to both specify the original parameter, and one for your own context type.
"""
