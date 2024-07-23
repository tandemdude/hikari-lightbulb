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

SCRIPT_PATHS = [
    os.path.join(".", "lightbulb"),
    os.path.join(".", "scripts"),
    os.path.join(".", "tests"),
    "noxfile.py",
    "docs/source/conf.py",
]

options.sessions = ["format_fix", "typecheck", "slotscheck", "test"]


@nox.session()
def format_fix(session: nox.Session) -> None:
    session.install(".[localization,crontrigger,dev.format]")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS)
    session.run("python", "-m", "ruff", "check", "--fix", *SCRIPT_PATHS)


@nox.session()
def format_check(session: nox.Session) -> None:
    session.install(".[localization,crontrigger,dev.format]")
    session.run("python", "-m", "ruff", "format", *SCRIPT_PATHS, "--check")
    session.run("python", "-m", "ruff", "check", "--output-format", "github", *SCRIPT_PATHS)


@nox.session()
def typecheck(session: nox.Session) -> None:
    session.install(".[localization,crontrigger,dev.typecheck]")
    session.run("python", "-m", "pyright")


@nox.session()
def slotscheck(session: nox.Session) -> None:
    session.install(".[localization,crontrigger,dev.slotscheck]")
    session.run("python", "-m", "slotscheck", "-m", "lightbulb")


@nox.session()
def test(session: nox.Session) -> None:
    session.install(".[localization,crontrigger,dev.test]")
    session.run("python", "-m", "pytest", "tests")


@nox.session(reuse_venv=True)
def sphinx(session: nox.Session) -> None:
    session.install(".[localization,crontrigger,dev.docs]")
    session.run("python", "./scripts/docs/api_reference_generator.py")
    session.run("python", "-m", "sphinx.cmd.build", "docs/source", "docs/build", "-b", "html")
