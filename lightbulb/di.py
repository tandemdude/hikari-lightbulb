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

__all__ = [
    "DI_ENABLED",
    "INJECTED",
    "AutocompleteContainer",
    "CircularDependencyException",
    "CommandContainer",
    "ContainerClosedException",
    "Contexts",
    "DefaultContainer",
    "DependencyInjectionException",
    "DependencyNotSatisfiableException",
    "If",
    "ListenerContainer",
    "TaskContainer",
    "Try",
    "with_di",
]

import typing as t

import linkd
from linkd import DI_ENABLED
from linkd import INJECTED
from linkd import CircularDependencyException
from linkd import ContainerClosedException
from linkd import DependencyInjectionException
from linkd import DependencyNotSatisfiableException
from linkd import If
from linkd import RootContainer as DefaultContainer
from linkd import Try
from linkd import inject as with_di


@t.final
class CommandContainer(linkd.Container):
    """Injectable type representing the dependency container for the command context."""

    __slots__ = ()


@t.final
class AutocompleteContainer(linkd.Container):
    """Injectable type representing the dependency container for the autocomplete context."""

    __slots__ = ()


@t.final
class ListenerContainer(linkd.Container):
    """Injectable type representing the dependency container for the listener context."""

    __slots__ = ()


@t.final
class TaskContainer(linkd.Container):
    """Injectable type representing the dependency container for the task context."""

    __slots__ = ()


@t.final
class Contexts:
    """Collection of the dependency injection context values Lightbulb uses."""

    __slots__ = ()

    # renaming this would be a majorly breaking change, so keeping it as DEFAULT for now
    DEFAULT = linkd.Contexts.ROOT
    """The base DI context - all other contexts are built with this as the parent."""
    COMMAND = linkd.global_context_registry.register("lightbulb.di.contexts.command", CommandContainer)
    """DI context used during command invocation, including for hooks and error handlers."""
    AUTOCOMPLETE = linkd.global_context_registry.register("lightbulb.di.contexts.autocomplete", AutocompleteContainer)
    """DI context used during autocomplete invocation."""
    LISTENER = linkd.global_context_registry.register("lightbulb.di.contexts.listener", ListenerContainer)
    """DI context used during listener invocation."""
    TASK = linkd.global_context_registry.register("lightbulb.di.contexts.task", TaskContainer)
    """DI context used during task invocation."""
