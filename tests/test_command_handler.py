# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
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
import mock
import pytest

from hikari.models import messages

from lightbulb import Bot
from lightbulb import commands
from lightbulb import context


@pytest.fixture()
def dummy_bot():
    return Bot(token="_", prefix="?")

@pytest.fixture()
def ctx():
    return mock.MagicMock(
        spec_set=context.Context(
            mock.MagicMock(spec_set=Bot),
            mock.MagicMock(spec_set=messages.Message),
            "",
            "",
            mock.MagicMock(spec_set=commands.Command),
        )
    )


def test_concatenate_args_with_asterisk(dummy_bot):
    # Check if _concatenate_arg concatenates last args correctly to match
    # with function's signature

    # dummy function for command
    def foo(ctx, arg1, arg2, *, arg3):
        pass

    cmd = commands.Command(foo, "", False, [])
    args = ["hello", "hey", "hello", "wassup"]

    assert dummy_bot._concatenate_args(args, cmd) == ["hello", "hey", "hello wassup"]


def test_concatenate_args_with_var_positional_arg(dummy_bot):
    # Check if function passes args correctly and check
    # if arg3 is a tuple

    # dummy function for command
    def foo(ctx, arg1, arg2, *arg3):
        return arg3

    cmd = commands.Command(foo, "", False, [])
    args = ["hey", "hello", "how", "are", "you"]

    # args list shouldn't change
    assert dummy_bot._concatenate_args(args, cmd) == args


def test_concatenate_args_with_positional_args(dummy_bot):
    # Check if function _concatenate_args works correctly
    # when foo takes only positional args

    def foo(ctx, arg1, arg2, arg3):
        pass

    cmd = commands.Command(foo, "", False, [])
    args = ["hey", "hello", "hi"]

    # No changes should be made to args in this test
    assert dummy_bot._concatenate_args(args, cmd) == args




