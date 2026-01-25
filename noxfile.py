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
import nox_uv
from nox import options

SCRIPT_PATHS = [
    os.path.join(".", "examples"),
    os.path.join(".", "lightbulb"),
    os.path.join(".", "scripts"),
    os.path.join(".", "tests"),
    "noxfile.py",
    "docs/source/conf.py",
]

options.sessions = ["format_fix", "typecheck", "slotscheck", "test"]
options.default_venv_backend, options.reuse_venv = "uv", "yes"


@nox_uv.session(uv_all_extras=True, uv_groups=["format"])
def format_fix(session: nox.Session) -> None:
    session.run("ruff", "format", *SCRIPT_PATHS)
    session.run("ruff", "check", "--fix", *SCRIPT_PATHS)


@nox_uv.session(uv_all_extras=True, uv_groups=["format"])
def format_check(session: nox.Session) -> None:
    session.run("ruff", "format", *SCRIPT_PATHS, "--check")
    session.run("ruff", "check", "--output-format", "github", *SCRIPT_PATHS)


@nox_uv.session(uv_all_extras=True, uv_groups=["test", "typecheck"])
def typecheck(session: nox.Session) -> None:
    session.run("pyright")


@nox_uv.session(uv_all_extras=True, uv_groups=["slotscheck"])
def slotscheck(session: nox.Session) -> None:
    session.run("slotscheck", "-m", "lightbulb")


@nox_uv.session(uv_all_extras=True, uv_groups=["test"])
def test(session: nox.Session) -> None:
    args = ["pytest"]
    if session.posargs:
        args.extend(["--cov", "lightbulb"])
    args.append("tests")

    session.run(*args)


@nox_uv.session(uv_all_extras=True, uv_groups=["docs"])
def sphinx(session: nox.Session) -> None:
    session.run("python", "./scripts/docs/api_reference_generator.py")

    html, epub, pdf = "html" in session.posargs, "epub" in session.posargs, "pdf" in session.posargs
    if not html and not epub and not pdf:
        html = epub = pdf = True

    if html:
        session.run("python", "-m", "sphinx.cmd.build", "docs/source", "docs/build/html", "-b", "html")
    if epub:
        session.run("python", "-m", "sphinx.cmd.build", "docs/source", "docs/build/epub", "-b", "epub")
    if pdf:
        session.run("python", "-m", "sphinx.cmd.build", "-M", "latexpdf", "docs/source", "docs/build/pdf")
