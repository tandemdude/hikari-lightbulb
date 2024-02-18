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
import os
import pathlib
import typing as t

API_REFERENCES_DIRECTORY = "docs", "source", "api-references"


class Module:
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path

    def write(self) -> None:
        parts = self.path.parts

        api_reference_dir_path = str(os.path.join(*API_REFERENCES_DIRECTORY, *parts[:-1]))
        os.makedirs(api_reference_dir_path, exist_ok=True)

        with open(os.path.join(api_reference_dir_path, parts[-1].replace(".py", ".rst")), "w") as fp:
            module_name = ".".join(parts)[:-3]
            fp.write(
                "\n".join(
                    [
                        "=" * len(module_name),
                        module_name,
                        "=" * len(module_name),
                        "",
                        f".. automodule:: {module_name}",
                        "    :members:",
                    ]
                )
            )


class Package:
    def __init__(
        self, path: pathlib.Path, header_override: t.Optional[str] = None, child_prefix: t.Optional[str] = None
    ) -> None:
        self.path = path
        self.header_override = header_override
        self.child_prefix = [child_prefix] if child_prefix else []

        self.packages = []
        self.modules = []

    def find_children(self) -> None:
        for item in self.path.iterdir():
            if is_package(item):
                self.packages.append(Package(item))
                continue

            if item.name.startswith("_") or not item.name.endswith(".py"):
                continue

            self.modules.append(Module(item))

    def write(self) -> None:
        self.find_children()
        for package in self.packages:
            package.write()
        for module in self.modules:
            module.write()

        parts = self.path.parts

        api_reference_dir_path = str(os.path.join(*API_REFERENCES_DIRECTORY, *parts[:-1]))
        os.makedirs(api_reference_dir_path, exist_ok=True)

        with open(os.path.join(api_reference_dir_path, parts[-1] + ".rst"), "w") as fp:
            package_name = self.header_override or ".".join(parts)

            package_lines = [
                f"    {'/'.join([*self.child_prefix, self.path.name, *package.path.relative_to(self.path).parts])}"
                for package in self.packages
            ]
            module_lines = [
                f"    {'/'.join([*self.child_prefix, self.path.name, *module.path.relative_to(self.path).parts])}"[:-3]
                for module in self.modules
            ]

            lines = [
                "=" * len(package_name),
                package_name,
                "=" * len(package_name),
                "",
            ]

            if package_lines:
                lines.extend(["**Subpackages:**", "", ".. toctree::", "    :maxdepth: 1", "", *package_lines, ""])
            if module_lines:
                lines.extend(["**Submodules:**", "", ".. toctree::", "    :maxdepth: 1", "", *module_lines, ""])

            fp.write("\n".join(lines).strip())


def is_package(path: pathlib.Path) -> bool:
    return path.is_dir() and (path / "__init__.py").is_file()


def run() -> None:
    Package(
        pathlib.Path("lightbulb"), header_override="API Reference", child_prefix=API_REFERENCES_DIRECTORY[-1]
    ).write()
    os.rename(
        os.path.join(*API_REFERENCES_DIRECTORY, "lightbulb.rst"),
        os.path.join(*API_REFERENCES_DIRECTORY[:-1], "api-reference.rst"),
    )


if __name__ == "__main__":
    run()
