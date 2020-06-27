from hikari.events.base import Event


class CommandErrorEvent(Event):
    """Event type to subscribe to for the processing of all command errors raised by the handler"""

    def __init__(self, error):
        self.error = error


class CommandError(Exception):
    """Base exception for the command handler"""

    pass


class CommandNotFound(CommandError):
    """Exception raised when a command when attempted to be invoked but one with that name could not be found"""

    def __init__(self, invoked_with: str):
        self.invoked_with = invoked_with
