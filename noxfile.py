# -*- coding: utf-8 -*-
# Copyright © Thomm.o 2021
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
from nox import options

PATH_TO_PROJECT = os.path.join(".", "lightbulb")
SCRIPT_PATHS = [
    PATH_TO_PROJECT,
    "noxfile.py",
    "release_webhook.py",
    "docs/source/conf.py",
]

options.sessions = ["format_fix", "test", "sphinx"]


@nox.session()
def test(session):
    session.install("-r", "test_requirements.txt")
    session.install("-r", "requirements.txt")
    session.run("python", "-m", "pytest", "tests", "--testdox")


@nox.session()
def format_fix(session):
    session.install("black")
    session.install("isort")
    session.run("python", "-m", "black", *SCRIPT_PATHS)
    session.run("python", "-m", "isort", *SCRIPT_PATHS)


# noinspection PyShadowingBuiltins
@nox.session()
def format(session):
    session.install("-U", "black")
    session.run("python", "-m", "black", *SCRIPT_PATHS, "--check")


@nox.session(reuse_venv=True)
def sphinx(session):
    session.install("-U", "sphinx", "sphinx_rtd_theme")
    session.install("-Ur", "requirements.txt")
    session.run("python", "-m", "sphinx.cmd.build", "docs/source", "docs/build", "-b", "html")


@nox.session(reuse_venv=True)
def mypy(session):
    # XXX: Re-enable these when done, too much of a waste of data
    # session.install("-Ur", "requirements.txt")
    # session.install("-U", "mypy", "lxml")
    session.run("python", "-m", "mypy", "-p", "lightbulb")  # "--html-report", "mypy_report")
