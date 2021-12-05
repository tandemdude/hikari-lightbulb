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
    "LightbulbError",
    "ApplicationCommandCreationFailed",
    "CommandNotFound",
    "CommandInvocationError",
    "CommandIsOnCooldown",
    "ConverterFailure",
    "NotEnoughArguments",
    "CheckFailure",
    "InsufficientCache",
    "NotOwner",
    "OnlyInGuild",
    "OnlyInDM",
    "BotOnly",
    "WebhookOnly",
    "HumanOnly",
    "NSFWChannelOnly",
    "ExtensionMissingUnload",
    "ExtensionNotFound",
    "ExtensionNotLoaded",
    "ExtensionMissingLoad",
    "ExtensionAlreadyLoaded",
    "CommandAlreadyExists",
    "MissingRequiredRole",
    "MissingRequiredPermission",
    "BotMissingRequiredPermission",
]

import typing as t

import hikari

if t.TYPE_CHECKING:
    from lightbulb import commands


class LightbulbError(Exception):
    """
    Base lightbulb exception class. All errors raised by lightbulb will be a subclass
    of this exception.
    """


class ApplicationCommandCreationFailed(LightbulbError):
    """Exception raised when initialisation of application commands fails."""


class ExtensionNotFound(LightbulbError):
    """Exception raised when an attempt is made to load an extension that does not exist."""


class ExtensionAlreadyLoaded(LightbulbError):
    """Exception raised when an extension already loaded is attempted to be loaded."""


class ExtensionMissingLoad(LightbulbError):
    """Exception raised when an extension is attempted to be loaded but does not contain a load function"""


class ExtensionMissingUnload(LightbulbError):
    """Exception raised when an extension is attempted to be unloaded but does not contain an unload function"""


class ExtensionNotLoaded(LightbulbError):
    """Exception raised when an extension not already loaded is attempted to be unloaded."""


class CommandAlreadyExists(LightbulbError):
    """
    Error raised when attempting to add a command to the bot but a name or alias
    for the command conflicts with a command that already exists.
    """


class CommandNotFound(LightbulbError):
    """
    Error raised when a command is attempted to be invoked but an implementation
    is not found. This will only be raised for prefix commands.
    """

    __slots__ = ("invoked_with",)

    def __init__(self, *args: t.Any, invoked_with: str) -> None:
        super().__init__(*args)
        self.invoked_with: str = invoked_with
        """The name or alias of the command that was used."""


class CommandInvocationError(LightbulbError):
    """
    Error raised when an error is encountered during command invocation. This
    wraps the original exception that caused it, which is accessible through
    ``CommandInvocationError.__cause__`` or ``CommandInvocationError.original``.
    """

    __slots__ = ("original",)

    def __init__(self, *args: t.Any, original: Exception) -> None:
        super().__init__(*args)
        self.original: Exception = original
        """The exception that caused this to be raised. Also accessible through ``CommandInvocationError.__cause__``"""
        self.__cause__ = original


class CommandIsOnCooldown(LightbulbError):
    """
    Error raised when a command was on cooldown when it was attempted to be invoked.
    """

    __slots__ = ("retry_after",)

    def __init__(self, *args: t.Any, retry_after: float) -> None:
        super().__init__(*args)
        self.retry_after: float = retry_after
        """The amount of time in seconds remaining until the cooldown expires."""


class ConverterFailure(LightbulbError):
    """
    Error raised when option type conversion fails while prefix command arguments are being parsed.
    """

    __slots__ = ("option",)

    def __init__(self, *args: t.Any, opt: commands.base.OptionLike) -> None:
        super().__init__(*args)
        self.option: commands.base.OptionLike = opt
        """The option that could not be converted."""


class NotEnoughArguments(LightbulbError):
    """
    Error raised when a prefix command expects more options than could be parsed from the user's input.
    """

    __slots__ = ("missing_options",)

    def __init__(self, *args: t.Any, missing: t.Sequence[commands.base.OptionLike]) -> None:
        super().__init__(*args)
        self.missing_options: t.Sequence[commands.base.OptionLike] = missing
        """The missing options from the command invocation."""


class CheckFailure(LightbulbError):
    """
    Error raised when a check fails before command invocation. If another error caused this
    to be raised then you can access it using ``CheckFailure.__cause__``.
    """


class InsufficientCache(CheckFailure):
    """
    Error raised when the cache is required for an operation but either could not be accessed
    or did not return the required object.
    """


class NotOwner(CheckFailure):
    """
    Error raised when a user who is not the owner of the bot attempts to use a command
    that is restricted to owners only.
    """


class OnlyInGuild(CheckFailure):
    """
    Error raised when a user attempts to use a command in DMs that has been restricted
    to being used only in guilds.
    """


class OnlyInDM(CheckFailure):
    """
    Error raised when a user attempts to use a command in a guild that has been restricted
    to being used only in DMs.
    """


class BotOnly(CheckFailure):
    """
    Error raised when any entity other than a bot attempts to use a command that has been
    restricted to being used only by bots.
    """


class WebhookOnly(CheckFailure):
    """
    Error raised when any entity other than a webhook attempts to use a command that has been
    restricted to being used only by webhooks.
    """


class HumanOnly(CheckFailure):
    """
    Error raised when any entity other than a human attempts to use a command that has been
    restricted to being used only by humans.
    """


class NSFWChannelOnly(CheckFailure):
    """
    Error raised when a user attempts to use a command in a non-NSFW channel that has
    been restricted to only being used in NSFW channels.
    """


class MissingRequiredRole(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more of the required roles.
    """


class MissingRequiredPermission(CheckFailure):
    """
    Error raised when the member invoking a command is missing one or more of the required permissions
    in order to be able to run the command.
    """

    def __init__(self, *args: t.Any, perms: hikari.Permissions) -> None:
        super().__init__(*args)
        self.missing_perms: hikari.Permissions = perms
        """The permissions that the member is missing."""


class BotMissingRequiredPermission(CheckFailure):
    """
    Error raised when the bot is missing one or more of the required permissions
    in order to be able to run the command.
    """

    def __init__(self, *args: t.Any, perms: hikari.Permissions) -> None:
        super().__init__(*args)
        self.missing_perms: hikari.Permissions = perms
        """The permissions that the bot is missing."""


class MissingRequiredAttachment(CheckFailure):
    """
    Error raised when an attachment is required for the command but none were supplied with the invocation.
    """
