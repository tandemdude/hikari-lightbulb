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
"""A simple, elegant, and powerful command handler for Hikari."""

from lightbulb import components
from lightbulb import di
from lightbulb import exceptions
from lightbulb import internal
from lightbulb import prefab
from lightbulb import utils
from lightbulb.client import *
from lightbulb.commands import *
from lightbulb.context import *
from lightbulb.loaders import *
from lightbulb.localization import *
from lightbulb.tasks import *

__all__ = [
    "DEFAULT_EXECUTION_STEP_ORDER",
    "AutocompleteContext",
    "Choice",
    "Client",
    "Context",
    "DictLocalizationProvider",
    "ExecutionHook",
    "ExecutionPipeline",
    "ExecutionStep",
    "ExecutionSteps",
    "GatewayEnabledClient",
    "GnuLocalizationProvider",
    "Group",
    "Loadable",
    "Loader",
    "MessageCommand",
    "Option",
    "OptionData",
    "RestContext",
    "RestEnabledClient",
    "SlashCommand",
    "SubGroup",
    "Task",
    "TaskExecutionData",
    "UserCommand",
    "attachment",
    "boolean",
    "channel",
    "client_from_app",
    "components",
    "crontrigger",
    "di",
    "exceptions",
    "hook",
    "integer",
    "internal",
    "invoke",
    "localization_unsupported",
    "mentionable",
    "number",
    "prefab",
    "role",
    "string",
    "uniformtrigger",
    "user",
    "utils",
]

# Do not change the below field manually. It is updated by CI upon release.
__version__ = "3.0.0a9"
