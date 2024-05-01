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
import argparse
import re
import sys

VERSION_REGEX = re.compile(r"__version__\s*=\s*\"(?P<version>\d+\.\d+\.\d+)(?:a(?P<alphanum>\d+))?\"")

parser = argparse.ArgumentParser()
parser.add_argument("type", choices=["major", "minor", "patch", "alpha"])
parser.add_argument("increment")

_noop = lambda n: n  # noqa: E731
_increment = lambda n: str(int(n) + 1)  # noqa: E731
_reset = lambda _: "0"  # noqa: E731

ACTIONS = {
    "major": (_increment, _reset, _reset, _reset),
    "minor": (_noop, _increment, _reset, _reset),
    "patch": (_noop, _noop, _increment, _reset),
    "alpha": (_noop, _noop, _noop, _increment),
}


def run(version_type: str, increment: str) -> None:
    with open("lightbulb/__init__.py") as fp:
        content = fp.read()

    current_version = VERSION_REGEX.search(content)
    if current_version is None:
        raise RuntimeError("Could not find version in __init__ file")

    version = current_version.groupdict()["version"]
    alpha = current_version.groupdict().get("alphanum", "0")

    if increment.lower() != "true":
        sys.stdout.write(f"{version}{('a' + alpha) if version_type.lower() == 'alpha' else ''}")
        return

    major, minor, patch = version.split(".")

    actions = ACTIONS[version_type.lower()]
    major, minor, patch, alpha = [a(s) for a, s in zip(actions, [major, minor, patch, alpha])]

    new_version = f"{major}.{minor}.{patch}"

    if version_type.lower() == "alpha":
        new_version += f"a{alpha}"

    updated_file_content = VERSION_REGEX.sub(f'__version__ = "{new_version}"', content)
    with open("lightbulb/__init__.py", "w") as fp:
        fp.write(updated_file_content)

    sys.stdout.write(new_version)


if __name__ == "__main__":
    args = parser.parse_args()
    run(args.type, args.increment)
