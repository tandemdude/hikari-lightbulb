# -*- coding: utf-8 -*-
# Copyright © tandemdude 2023-present
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
import argparse
import re
import sys

VERSION_REGEX = re.compile(r"__version__\s*=\s*\"(?P<version>\d+\.\d+\.\d+)(?:\.dev(?P<devnum>\d+))?\"")

parser = argparse.ArgumentParser()
parser.add_argument("type", choices=["major", "minor", "patch", "dev"])
parser.add_argument("increment")

_noop = lambda n: n  # noqa: E731
_increment = lambda n: str(int(n) + 1)  # noqa: E731
_reset = lambda _: "0"  # noqa: E731

ACTIONS = {
    "major": (_increment, _reset, _reset, _reset),
    "minor": (_noop, _increment, _reset, _reset),
    "patch": (_noop, _noop, _increment, _reset),
    "dev": (_noop, _noop, _noop, _increment),
}


def run(version_type: str, increment: str) -> None:
    with open("lightbulb/__init__.py") as fp:
        content = fp.read()

    current_version = VERSION_REGEX.search(content)
    if current_version is None:
        raise RuntimeError("Could not find version in __init__ file")

    version = current_version.groupdict()["version"]
    dev = current_version.groupdict().get("devnum", "0")

    if increment.lower() != "true":
        sys.stdout.write(f"{version}{('.dev' + dev) if version_type.lower() == 'dev' else ''}")
        return

    major, minor, patch = version.split(".")

    actions = ACTIONS[version_type.lower()]
    major, minor, patch, dev = [a(s) for a, s in zip(actions, [major, minor, patch, dev])]

    new_version = f"{major}.{minor}.{patch}"

    if version_type.lower() == "dev":
        new_version += f".dev{dev}"

    updated_file_content = VERSION_REGEX.sub(f'__version__ = "{new_version}"', content)
    with open("lightbulb/__init__.py", "w") as fp:
        fp.write(updated_file_content)

    sys.stdout.write(new_version)


if __name__ == "__main__":
    args = parser.parse_args()
    run(args.type, args.increment)
