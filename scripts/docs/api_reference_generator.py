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
import collections
import importlib
import inspect
import os
import pathlib
import re
import typing as t

API_REFERENCES_DIRECTORY = "docs", "source", "api-references"

# Regex to match special modifiers that can change the output when writing reST
#
# Implemented modifiers:
# - api_ref_gen::ignore - ignores the current file, does not output a reST file
# - api_ref_gen::add_autodoc_option::<option> - adds a directive to the '.. automodule::' block for this module
MODIFIER_DIRECTIVE_REGEX = re.compile(r"^#\s*api_ref_gen::(?P<directive>\w+)(?:::(?P<parameter>.+))?$")


def is_package(path: pathlib.Path) -> bool:
    return path.is_dir() and (path / "__init__.py").is_file()


class Module:
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path

    def write(self) -> bool:
        # Find the modifier directives in the file
        modifiers: dict[str, list[str | None]] = collections.defaultdict(list)
        with open(self.path) as module:
            content = module.readlines()
            for line in content[:10]:
                if match := MODIFIER_DIRECTIVE_REGEX.fullmatch(line.strip()):
                    modifiers[match.group("directive")].append(match.group("parameter"))

        # Skip ignored files
        if "ignore" in modifiers:
            return False

        parts = self.path.parts

        api_reference_dir_path = str(os.path.join(*API_REFERENCES_DIRECTORY, *parts[:-1]))
        os.makedirs(api_reference_dir_path, exist_ok=True)

        with open(os.path.join(api_reference_dir_path, parts[-1].replace(".py", ".rst")), "w") as fp:
            module_name = ".".join(parts)[:-3]

            lines = [
                "=" * len(module_name),
                module_name,
                "=" * len(module_name),
                "",
                f".. automodule:: {module_name}",
                "    :members:",
            ]
            for extra_option in set(filter(None, modifiers["add_autodoc_option"])):
                lines.append(f"    :{extra_option}:")

            fp.write("\n".join(lines))

        return True


class Package:
    def __init__(
        self,
        path: pathlib.Path,
        header_override: t.Optional[str] = None,
        child_prefix: t.Optional[str] = None,
        is_root: bool = False,
    ) -> None:
        self.path = path
        self.header_override = header_override
        self.child_prefix = [child_prefix] if child_prefix else []
        self.is_root = is_root

        self.packages: list[Package] = []
        self.modules: list[Module] = []

    def find_children(self) -> None:
        for item in self.path.iterdir():
            if is_package(item):
                self.packages.append(Package(item))
                continue

            if item.name.startswith("_") or not item.name.endswith(".py"):
                continue

            self.modules.append(Module(item))

    def write(self) -> bool:
        written_packages: list[Package] = []
        written_modules: list[Module] = []

        self.find_children()
        for package in self.packages:
            if package.write():
                written_packages.append(package)
        for module in self.modules:
            if module.write():
                written_modules.append(module)

        # If no pages were written for any subpackage or submodule then we don't need a page for this package
        if not written_packages and not written_modules:
            return False

        parts = self.path.parts

        api_reference_dir_path = str(os.path.join(*API_REFERENCES_DIRECTORY, *parts[:-1]))
        os.makedirs(api_reference_dir_path, exist_ok=True)

        with open(os.path.join(api_reference_dir_path, parts[-1] + ".rst"), "w") as fp:
            package_name = ".".join(parts)
            header_text = self.header_override or package_name

            package_lines = [
                f"    {'/'.join([*self.child_prefix, self.path.name, *package.path.relative_to(self.path).parts])}"
                for package in written_packages
            ]
            module_lines = [
                f"    {'/'.join([*self.child_prefix, self.path.name, *module.path.relative_to(self.path).parts])}"[:-3]
                for module in written_modules
            ]

            lines = [
                "=" * len(header_text),
                header_text,
                "=" * len(header_text),
                "",
                ".. automodule:: " + package_name,
                "",
            ]

            if package_lines:
                lines.extend(
                    ["**Subpackages:**", "", ".. toctree::", "    :maxdepth: 1", "", *sorted(package_lines), ""]
                )
            if module_lines:
                lines.extend(["**Submodules:**", "", ".. toctree::", "    :maxdepth: 1", "", *sorted(module_lines), ""])

            # Include a list of exported members in each package
            root_module = importlib.import_module(package_name)

            root_members: list[str] = []
            for member in sorted(getattr(root_module, "__all__", [])):
                item = getattr(root_module, member)
                if inspect.ismodule(item):
                    root_members.append(f"- :doc:`{member} <api-references/{'/'.join(item.__name__.split('.'))}>`")
                elif inspect.isclass(item):
                    root_members.append(f"- :class:`~{item.__module__}.{member}`")
                elif inspect.isfunction(item):
                    root_members.append(
                        f"- :{'meth' if inspect.ismethod(item) else 'func'}:`~{item.__module__}.{member}`"
                    )
                else:
                    root_members.append(f"- :obj:`~lightbulb.{member}`")

            if root_members:
                # fmt: off
                lines.extend([
                    "++++++++++++++++",
                    "Exported Members",
                    "++++++++++++++++",
                    "",
                    "The following members are exported to the top level of this package and so can be accessed "
                    f"using ``{package_name}.<member>`` instead of requiring you to use the full import path.",
                    "",
                ])
                # fmt: on

                n_exported_table_columns = 3
                lines.extend([".. list-table::", ""])
                for i, elem in enumerate(root_members):
                    lines.append(f"    {' ' if i % n_exported_table_columns else '*'} {elem}")
                if n_last_row := (len(root_members) % n_exported_table_columns):
                    lines.extend(["      -" for _ in range(n_exported_table_columns - n_last_row)])
                lines.append("")

            fp.write("\n".join(lines).strip())

        return True


def run() -> None:
    Package(
        pathlib.Path("lightbulb"),
        header_override="API Reference",
        child_prefix=API_REFERENCES_DIRECTORY[-1],
        is_root=True,
    ).write()
    os.rename(
        os.path.join(*API_REFERENCES_DIRECTORY, "lightbulb.rst"),
        os.path.join(*API_REFERENCES_DIRECTORY[:-1], "api-reference.rst"),
    )


if __name__ == "__main__":
    run()
