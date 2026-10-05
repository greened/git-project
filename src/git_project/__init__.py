# SPDX-FileCopyrightText: 2020-present David A. Greene <dag@obbligato.org>

# SPDX-License-Identifier: AGPL-3.0-or-later

# Copyright 2024 David A. Greene

# This file is part of git-project

# git-project is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License along
# with git-project. If not, see <https://www.gnu.org/licenses/>.

"""
===================================================
git-project - The extensible stupid project manager
===================================================

|VersionImageLink|_

|PythonVersionImageLink|_

.. |VersionImageLink| image:: https://img.shields.io/pypi/v/git-project.svg
.. _VersionImageLink: https://pypi.org/project/git-project
.. |PythonVersionImageLink| image:: https://img.shields.io/pypi/pyversions/git-project.svg
.. _PythonVersionImageLink: https://pypi.org/project/git-project

-------

Installation
============
::

   pip install git-project
   pip install git-project-core-plugins

git-project needs Python 3.10 or later.

Overview
========

git-project is a git extension for managing development work in a git
repository. By itself it does almost nothing. It provides ``-h``,
``--version`` and ``--menu``, and plugins provide the commands.

`git-project-core-plugins
<https://github.com/greened/git-project-core-plugins>`_ provides the basic
commands, among them ``clone``, ``init``, ``worktree``, ``branch``, ``run``
and ``config``. Install it alongside git-project.

git-project aims to make switching between tasks in a repository fast,
without losing the state of the tasks you set aside. For example, the core
plugins can give each worktree its own build directory, so moving to another
worktree does not rebuild everything.

Projects
========

git-project runs under the name of a link to it, and that name selects the
*active project*. If ``git-fizzbin`` is a symlink to ``git-project``, then
``git fizzbin <command>`` runs git-project with ``fizzbin`` as the active
project. Run as ``git-project`` itself, the active project is ``project``.
These docs write ``git <project>`` for whichever name you use.

Create the link yourself, in a directory on your ``PATH``::

  ln -s "$(command -v git-project)" ~/.local/bin/git-fizzbin

Each project keeps its settings apart from the others, so one repository can
hold several projects, each run through its own link.

Configuration
=============

git-project stores its settings in the repository's git config. A project's
settings live in a section named after the project. git-project changes
``.`` and ``_`` in the name to ``-``, so the project ``fizz_bin`` uses the
section ``fizz-bin``.

Whenever they are missing, git-project sets two values in the project
section: ``branch``, the repository's main branch, and ``remote``, which is
``origin``.

Plugins keep their own settings in subsections of the project section. For
example, a project with one worktree might hold::

  [fizzbin]
      branch = main
      remote = origin
      srcdir = /src
  [fizzbin "worktree.main"]
      builddir = {srcdir}/build

A key can hold more than one value. On every run, git-project also checks
the config file and stops if one section holds the same ``key = value`` line
twice.

Scopes
======

A *scope* is a subsection that a plugin makes active for the current run.
While a scope is active, a value set in the scope overrides the same key in
the project section. For example, when you run inside a worktree, the core
plugins' ``worktree`` plugin makes that worktree's subsection a scope. A
value set for one worktree then applies only there.

The name of an active scope is also a substitution variable, and its value
is the scope's identifier. In the example above, ``{worktree}`` is ``main``
inside the ``main`` worktree.

Substitution
============

Some values are *substituted* before they are used, for example the
commands that the ``run`` plugin runs. Substitution replaces ``{name}`` with
the value of ``name``. A name can be:

* a key in the project section
* a key in the object being substituted, or in an active scope
* the name of an active scope, as above
* one of these built-in names

``project``
    The active project's section name
``branch``
    The checked-out branch, or during a rebase the branch being rebased
``gitdir``
    The repository's git directory
``git_common_dir``
    The git directory that all worktrees share
``git_workdir``
    The root of the current worktree

Substitution repeats until the value stops changing, so a value can name
another value that itself contains ``{name}``. A value may not name itself.
To write a literal brace, write ``{{}`` for ``{`` and ``{}}`` for ``}``.

**A value is evaluated as Python.** git-project substitutes a value by
evaluating it as a Python f-string. So ``{1+1}`` becomes ``2``, and any
Python expression in braces runs when the value is substituted. Treat the
git config as code, and do not include config from a source you do not
trust. A value that contains a ``'`` cannot be substituted.

Getting help
============

``git <project> -h`` lists the commands that the installed plugins provide.
Use ``-h`` there, because git turns ``git <project> --help`` into a request
for a man page. After a command name ``--help`` works as usual, and with the
core plugins installed ``git <project> help <command>`` shows a command's
full manual.

``--menu`` lists a command's subcommands, arguments and options in a form meant
for tools.

License
=======
`git-project` is distributed under the terms of the `GNU Affero General Public License v3.0 or later`_.

.. _`GNU Affero General Public License v3.0 or later`: https://spdx.org/licenses/AGPL-3.0-or-later.html

"""

from .commandline import (
    add_top_level_command,
    get_or_add_top_level_command,
    parse_arguments,
)
from .configobj import ConfigObject
from .exception import GitProjectError
from .git import Git
from .gitproject import GitProject
from .main import main_impl
from .parsermanager import ParserManager
from .plugin import Plugin
from .pluginmanager import PluginManager
from .project import Project
from .runnable import RunnableConfigObject
from .scopedobj import ScopedConfigObject
from .shell import capture_command, iter_command, run_command_with_shell
from .substitutable import SubstitutableConfigObject

__all__ = [
    "ConfigObject",
    "Git",
    "GitProject",
    "GitProjectError",
    "ParserManager",
    "Plugin",
    "PluginManager",
    "Project",
    "RunnableConfigObject",
    "ScopedConfigObject",
    "SubstitutableConfigObject",
    "add_top_level_command",
    "capture_command",
    "get_or_add_top_level_command",
    "iter_command",
    "main_impl",
    "parse_arguments",
    "run_command_with_shell",
]
