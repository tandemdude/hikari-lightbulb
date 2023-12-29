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

options.sessions = ["format_fix", "typecheck", "slotscheck"]


@nox.session()
def format_fix(session):
    session.install("-Ur", "dev-requirements/formatting.txt")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS)
    session.run("python", "-m", "ruff", "--fix", *SCRIPT_PATHS)


@nox.session()
def format_check(session):
    session.install("-Ur", "dev-requirements/formatting.txt")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS, "--check")
    session.run("python", "-m", "ruff", "--output-format", "github", *SCRIPT_PATHS)


@nox.session()
def typecheck(session):
    session.install("-Ur", "requirements.txt")
    session.install("-Ur", "crontrigger_requirements.txt")
    session.install("-Ur", "dev-requirements/pyright.txt")
    session.run("python", "-m", "pyright")


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
