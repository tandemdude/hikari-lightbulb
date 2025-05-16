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
"""
This module contains utilities for parsing your application configuration from various file types. Along with
basic deserializing to Python objects, it implements environment variable substitution expressions to allow
"dynamic" values within the configuration.

These utilities were originally implemented within lightbulb, but since have been extracted and are now
provided by the ``confspec`` library (`PyPI <https://pypi.org/project/confspec/>`_).

Environment Variable Substitution
---------------------------------

The basic syntax for defining a variable substitution is as follows:

.. code-block:: yaml

    ${VARIABLE_NAME}

This would be replaced by the loader with the value of the environment variable ``VARIABLE_NAME`` while parsing
the configuration. If the variable is not set, then this will evaluate to an empty string.

Expanding on this, you can also specify default values for when a variable is not set:

.. code-block:: yaml

    ${VARIABLE_NAME:default-value}

This will expand to the value of ``VARIABLE_NAME``, if it is set, otherwise it will expand to whatever you specified
as the default value.

Sometimes you may want to include text that uses the ``${NAME}`` format directly, without any substitution. This
can be achieved by escaping the substitution expression with an additional ``$`` symbol:

.. code-block:: yaml

    $${VARIABLE_NAME}

This will not be expanded using the environment variables, and instead one of the leading ``$`` symbols will be
stripped, causing it to evaluate as ``${VARIABLE_NAME}``.

``confspec`` provides additional substitution features, you should consult its documentation for further details.

Usage
-----

``confspec`` supports parsing configuration into a variety of formats - standard dictionaries, msgspec Structs, or
pydantic models. The below example will use msgspec Structs, but you can choose whichever you are most comfortable
with. Just ensure the correct dependencies are installed first.

You should create a configuration file for your application - supported
formats are ``yaml``, ``toml`` and ``json`` - and a :obj:`msgspec.Struct`-derived class that your configuration
will be deserialized to.

``config.yaml``

.. code-block:: yaml

    foo: bar
    baz: ${INT_VAR}
    bork:
      qux: quux

``config.py``

.. code-block:: python

    class BorkConfig(msgspec.Struct):
        qux: str

    class Config(msgspec.Struct):
        foo: str
        baz: int
        bork: BorkConfig

Then to parse the config file into your models, simply call the :meth:`~load` method:

.. code-block:: python

    import lightbulb
    # your configuration models
    from app import config

    parsed_cfg = lightbulb.config.load("path/to/config.yaml", cls=config.Config)
    # prints "bar"
    print(parsed_cfg.foo)
"""

from __future__ import annotations

__all__ = ["load", "loads"]

from confspec import load
from confspec import loads
