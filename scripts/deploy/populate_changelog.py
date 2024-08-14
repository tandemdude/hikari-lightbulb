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

CHANGE_LOCATION_MARKER = "<!-- next-changelog -->\n"

parser = argparse.ArgumentParser()
parser.add_argument("new_changes_path")
parser.add_argument("changelog_path")


def main(new_changes_path: str, changelog_path: str) -> None:
    with open(new_changes_path) as fp:
        new_changes = fp.read().strip()

        new_changes_lines = new_changes.splitlines()
        # Remove the hash and whitespace from the first line
        new_changes_lines[0] = new_changes_lines[0].strip().strip("#").strip()
        # Remove the underline (I can't be bothered to make my own template
        new_changes_lines.pop(1)
        # Add the h2 prefix for the version number
        new_changes = "## " + "\n".join(new_changes_lines)

    with open(changelog_path) as fp:
        changelog_contents = fp.read()

    if CHANGE_LOCATION_MARKER not in changelog_contents:
        raise RuntimeError("cannot find location to place changelog")

    new_changes = f"{CHANGE_LOCATION_MARKER}\n{new_changes}\n\n----\n"
    changelog_contents = changelog_contents.replace(CHANGE_LOCATION_MARKER, new_changes)

    with open(changelog_path, "w") as fp:
        fp.write(changelog_contents)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.new_changes_path, args.changelog_path)
