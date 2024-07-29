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
"""A simple-to-use command handler for Hikari."""

from lightbulb import di
from lightbulb import exceptions
from lightbulb import internal
from lightbulb import utils
from lightbulb.client import *
from lightbulb.commands import *
from lightbulb.context import *
from lightbulb.loaders import *
from lightbulb.localization import *
from lightbulb.tasks import *

__all__ = [
    "di",
    "exceptions",
    "internal",
    "utils",
    "DEFAULT_EXECUTION_STEP_ORDER",
    "Client",
    "GatewayEnabledClient",
    "RestEnabledClient",
    "client_from_app",
    "SlashCommand",
    "MessageCommand",
    "UserCommand",
    "ExecutionStep",
    "ExecutionSteps",
    "ExecutionHook",
    "ExecutionPipeline",
    "hook",
    "invoke",
    "SubGroup",
    "Group",
    "Choice",
    "OptionData",
    "Option",
    "string",
    "integer",
    "boolean",
    "number",
    "user",
    "channel",
    "role",
    "mentionable",
    "attachment",
    "AutocompleteContext",
    "Context",
    "RestContext",
    "Loadable",
    "Loader",
    "localization_unsupported",
    "DictLocalizationProvider",
    "GnuLocalizationProvider",
    "uniformtrigger",
    "crontrigger",
    "TaskExecutionData",
    "Task",
]

# Do not change the below field manually. It is updated by CI upon release.
__version__ = "3.0.0a8"
