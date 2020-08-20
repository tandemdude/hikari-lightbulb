# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2020
#
# This file is part of Hikari Command Handler.
#
# Hikari Command Handler is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari Command Handler is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari Command Handler. If not, see <https://www.gnu.org/licenses/>.
import os

import nox

PATH_TO_PROJECT = os.path.join(".", "lightbulb")
SCRIPT_PATHS = [
    PATH_TO_PROJECT,
    "noxfile.py",
    "release_webhook.py",
    "docs/source/conf.py",
]


@nox.session(python=["3.8"])
def test(session):
    session.install("-r", "test_requirements.txt")
    session.install("-r", "requirements.txt")
    session.run("python", "-m", "pytest", "tests", "--testdox")


@nox.session(python=["3.8"])
def format_fix(session):
    session.install("black")
    session.install("isort")
    session.run("python", "-m", "black", *SCRIPT_PATHS)
    session.run("python", "-m", "isort", *SCRIPT_PATHS)


# noinspection PyShadowingBuiltins
@nox.session(python=["3.8"])
def format(session):
    session.run("pip", "install", "-U", "black")
    session.run("python", "-m", "black", *SCRIPT_PATHS, "--check")


@nox.session(python=["3.8"], reuse_venv=True)
def sphinx(session):
    session.install("-U", "sphinx", "sphinx_rtd_theme")
    session.install("-Ur", "requirements.txt")
    session.run("python", "-m", "sphinx.cmd.build", "docs/source", "docs/build", "-b", "html")
