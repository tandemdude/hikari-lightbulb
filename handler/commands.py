import typing
import logging
import inspect


class Command:
    def __init__(self, callable: typing.Callable):
        self.callback = callable
        self.name = callable.__name__
        self.help: typing.Optional[str] = inspect.getdoc(callable)

    async def __call__(self, *args, **kwargs):
        await self.callback(*args)

    @classmethod
    def from_callable(cls, callable: typing.Callable):
        return cls(callable)
