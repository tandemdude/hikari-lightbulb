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
from setuptools import setup, find_namespace_packages
from lightbulb import __version__ as lightbulb_version

name = "lightbulb"


def long_description():
    with open("README.md") as fp:
        return fp.read()


def parse_requirements_file(path):
    with open(path) as fp:
        dependencies = (d.strip() for d in fp.read().split("\n") if d.strip())
        return [d for d in dependencies if not d.startswith("#")]


setup(
    name="hikari-lightbulb",
    version=lightbulb_version,
    description="A simple to use command handler for Hikari",
    long_description=long_description(),
    long_description_content_type="text/markdown",
    author="tandemdude",
    author_email="tandemdude1@gmail.com",
    url="https://gitlab.com/tandemdude/lightbulb",
    packages=find_namespace_packages(include=[name + "*"]),
    license="LGPL-3.0-ONLY",
    install_requires=parse_requirements_file("requirements.txt"),
    python_requires=">=3.8.0,<3.10",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: 3 :: Only",
    ],
)