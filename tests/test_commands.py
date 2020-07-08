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

from lightbulb import commands


@pytest.fixture()
def dummy_function():
    return lambda _: _


@pytest.fixture()
def dummy_command():
    return commands.Command((lambda _: _), "dummy", True, [])


@pytest.fixture()
def dummy_group():
    return commands.Group((lambda _: _), "dummy", True, [])


def test_command_decorator_returns_Command(dummy_function):
    assert isinstance(commands.command()(dummy_function), commands.Command)


def test_group_decorator_returns_Group(dummy_function):
    assert isinstance(commands.group()(dummy_function), commands.Group)


def test_Command_name_property_returns_name(dummy_command):
    assert dummy_command.name == "dummy"


def test_Command_is_subcommand_returns_False(dummy_command):
    assert dummy_command.is_subcommand is False


def test_Command_invoke_calls_callable(dummy_command):
    dummy_callback = mock.Mock()
    dummy_command._callback = dummy_callback
    dummy_command.invoke("foo")
    dummy_callback.assert_called_with("foo")


def test_Command_add_check_adds_callable_to_list(dummy_command, dummy_function):
    dummy_command.add_check(dummy_function)
    assert dummy_command._checks == [dummy_function]


def test_Command_args_before_asterisk_return(dummy_command):
    args_num, name = dummy_command.arg_details._args_and_name_before_asterisk()
    assert args_num == 0


def test_Command_args_before_asterisk_raise_error():
    # Check if _args_before_asterisk raises TypeError after having more than 1 arg after asterisk

    def dummy_function(a, b, *, c, d):
        pass

    with pytest.raises(TypeError) as error:
        dummy_cmd = commands.Command(dummy_function, "dummy", True, [])
        dummy_cmd.arg_details._args_and_name_before_asterisk()

    assert error.type is TypeError


def test_Group_get_subcommand_returns_None(dummy_group):
    assert dummy_group.get_subcommand("foo") is None


def test_Group_get_subcommand_returns_command(dummy_group, dummy_command):
    dummy_group.subcommands["foo"] = dummy_command
    assert dummy_group.get_subcommand("foo") is dummy_command
