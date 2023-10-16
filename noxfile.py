# -*- coding: utf-8 -*-
# Copyright © tandemdude 2020-present
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
    "release_helpers.py",
    "docs/source/conf.py",
]

options.sessions = ["format_fix", "mypy", "slotscheck"]


@nox.session()
def format_fix(session):
    session.install("-Ur", "dev-requirements/formatting.txt")
    session.run("python", "-m", "black", *SCRIPT_PATHS)
    session.run("python", "-m", "ruff", "--fix", *SCRIPT_PATHS)


# noinspection PyShadowingBuiltins
@nox.session()
def format_check(session):
    session.install("-Ur", "dev-requirements/formatting.txt")
    session.run("python", "-m", "black", *SCRIPT_PATHS, "--check")
    session.run("python", "-m", "ruff", "--output-format", "github", *SCRIPT_PATHS)


@nox.session()
def mypy(session):
    session.install("-Ur", "requirements.txt")
    session.install("-Ur", "crontrigger_requirements.txt")
    session.install("-Ur", "dev-requirements/mypy.txt")
    session.run("python", "-m", "mypy", "lightbulb")


@nox.session()
def slotscheck(session):
    session.install("-Ur", "requirements.txt")
    session.install("-Ur", "crontrigger_requirements.txt")
    session.install("-Ur", "dev-requirements/slotscheck.txt")
    session.run("python", "-m", "slotscheck", "-m", "lightbulb")


@nox.session(reuse_venv=True)
def sphinx(session):
    session.install("-Ur", "dev-requirements/docs.txt")
    session.install("-Ur", "crontrigger_requirements.txt")
    session.install("-Ur", "requirements.txt")
    session.run("python", "-m", "sphinx.cmd.build", "docs/source", "docs/build", "-b", "html")
