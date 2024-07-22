# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))
sys.setrecursionlimit(1500)


# -- Project information -----------------------------------------------------

project = "Lightbulb"
copyright = "2020-present, tandemdude"
author = "tandemdude"

with open("../../lightbulb/__init__.py") as fp:
    file = fp.read()
version = re.search(r"__version__ = \"([^\"]+)", file).group(1)
release = version

master_doc = "index"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinx_design",
    "sphinx_prompt",
    "notfound.extension",
    "sphinxext.opengraph",
    "sphinxcontrib.mermaid",
]
myst_enable_extensions = ["colon_fence"]

autodoc_default_options = {"member-order": "groupwise"}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "hikari": ("https://docs.hikari-py.dev/en/latest", None),
    "aiohttp": ("https://docs.aiohttp.org/en/stable/", None),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_logo = "_static/logo.png"

ogp_image = "_static/logo.png"
ogp_site_name = "Hikari Lightbulb Documentation"

add_module_names = False
modindex_common_prefix = ["lightbulb."]
python_use_unqualified_type_names = True
python_display_short_literal_types = True
# python_maximum_signature_line_length = 1
