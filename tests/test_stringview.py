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
import pytest

from lightbulb import stringview
from lightbulb import errors


def test_stringview_splits_normal_args():
    sv = stringview.StringView("I am thommo")
    assert sv.deconstruct_str() == (["I", "am", "thommo"], "")


def test_stringview_splits_quoted_args():
    sv = stringview.StringView('I "am thommo"')
    assert sv.deconstruct_str() == (["I", "am thommo"], "")


def test_stringview_raises_UnclosedQuotes():
    sv = stringview.StringView('I "am thommo')
    with pytest.raises(errors.UnclosedQuotes) as exc_info:
        sv.deconstruct_str()
    assert exc_info.type is errors.UnclosedQuotes
