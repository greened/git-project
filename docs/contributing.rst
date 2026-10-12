..
    SPDX-FileCopyrightText: 2026-present David A. Greene <dag@obbligato.org>

..
    SPDX-License-Identifier: AGPL-3.0-or-later

..
    Copyright 2026 David A. Greene

..
    This file is part of git-project

..
    git-project is free software: you can redistribute it and/or modify it under
    the terms of the GNU Affero General Public License as published by the Free
    Software Foundation, either version 3 of the License, or (at your option)
    any later version.

..
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
    for more details.

..
    You should have received a copy of the GNU Affero General Public License
    along with git-project. If not, see <https://www.gnu.org/licenses/>.

Working on git-project
======================

This guide is for changing git-project itself. For writing a plugin, see
:mod:`git_project.plugin`. For how a run proceeds, see
:mod:`git_project.main`.

Layout
------

``src/git_project``
    The package. ``test_support`` is part of it, not of the tests, because
    plugins test with its fixtures too.
``tests``
    The test suite. ``tests/conftest.py`` imports the fixtures from
    ``git_project.test_support``.
``docs``
    The Sphinx sources. The pages mostly pull in docstrings.

Environment
-----------

git-project builds with hatch, and its version comes from git through
hatch-vcs. The default hatch environment installs git-project-core-plugins
from the package index. The command-line tests need its commands, since
git-project alone has none.

That environment gets the PUBLISHED core-plugins. To test against a local
core-plugins checkout, make a virtual environment with both installed
editable, for example with uv::

  uv venv /tmp/gp-env
  uv pip install --python /tmp/gp-env/bin/python \
    -e <git-project checkout> -e <core-plugins checkout> \
    pytest pytest-console-scripts

Put that environment's ``bin`` first on ``PATH`` when running the tests,
because the command-line tests run the ``git-project`` script.

Tests
-----

.. automodule:: git_project.test_support

Lint
----

``hatch run lint:all`` runs ruff, ``black --check`` and mypy.
``hatch run lint:fmt`` runs black, then ``ruff check --fix``. The lint
environment pins each tool to an exact version.

Documentation
-------------

Docstrings are the one source for the package, module, class and command
documentation, and each one reaches a fixed place:

- The package docstring, in ``__init__.py``, is the PyPI description and
  the first page of the Sphinx docs. The fragments in ``pyproject.toml``
  split it at its first ``-------`` line, which follows the badges, so keep
  that line where it is.
- The ``commandline`` module docstring is the description that
  ``git <project> -h`` shows.
- A plugin's class docstring is the manual that the help plugin shows.
- Other module and class docstrings appear on the Sphinx pages, which only
  pull them in with ``automodule`` and ``autoclass``.

So do not copy docstring text into a ``.rst`` file. Change the docstring.
This page, the changelog and the authors list are written in ``docs``
directly, and the license page includes ``COPYING``.

``hatch run docs:build`` builds the Sphinx docs and fails on any warning.
Check the PyPI description with ``twine check`` on a built wheel.

Changelog
---------

A branch with a change a user can see adds a fragment to ``changelog.d``,
named ``<slug>.<category>.rst``. The slug is lower case letters, digits
and hyphens. The branch name makes a good one, lower-cased with ``/`` and
``_`` turned into ``-``. A second fragment takes a suffix such as
``-2``. The category is ``added``, ``changed``, ``deprecated``,
``removed``, ``fixed`` or ``security``. A branch never edits
``docs/changelog.rst``.

Each fragment is one entry in plain RST, with no Sphinx roles, because
the PyPI description shows the newest release's section. Put code in
double backticks and write a link inline, as ```text <URL>`__``. Describe
what changed for someone using the last release, not what changed in the
tree. Line breaks are kept, and an entry may have several paragraphs. A
defect that no release ever had needs no fragment.

Releasing
---------

A release is a tag on the main branch, named ``vX.Y.Z``. Tags are
lightweight. hatch-vcs takes the version from the tag, so there is no
version number to edit.

#. Run ``./changelog.py --version X.Y.Z``. It moves the fragments into a
   new section of the changelog, dated today, and stages their removal.
   With ``--stdout`` it prints the section and changes nothing.
#. Edit and review the result. Commit the changelog with the removed
   fragments and push that commit to the main branch.
#. Tag that commit.
#. Build from a clean checkout of the tagged commit, such as a new
   worktree, with ``hatch build``. An untracked file in the checkout ends up
   in the sdist.
#. Check that the built files say ``X.Y.Z``, with no ``.dev`` or ``+g``
   suffix. A suffix means the build did not see the tag.
#. Run ``twine check`` on the built files, then upload them with ``twine
   upload``. A version number can never be uploaded twice.
#. Push the tag last, so a failed upload leaves no published tag behind.

``changelog.py`` refuses, and changes nothing, when a fragment or the
changelog would give a wrong section. Its docstring lists every case.

git-project-core-plugins declares its floor on git-project in its
``requirements.txt``. When core-plugins needs something new in git-project,
release git-project first, raise that floor, and then release core-plugins.
