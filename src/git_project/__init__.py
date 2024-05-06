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
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

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

Description
===========

git-project is a git extension to manage development of a project hosted in a
git repository.  By itself git-project does almost nothing.  Its functionality
is enhanced by plugins.

`git-project-core-plugins
<http://www.github.com/greened/git-project-core-plugins>`_ provides a set of
basic functionality and should almost always be installed alongside git-project.

Conventions
===========

Symlinks identiy projects to the ``git-project`` command.  For example, if
``git-fizzbin`` is symlinked to ``git-project``, then ``git fizzbin <command>``
will invoke ``git-project`` with ``fizzbin`` as the "active project."  To
emphasize this, we show git-project commands with a generic ``<project>``
identifier::

  git <project> --help

Discussion
==========

With git-project and its core plugins you can:

* Initialize a development environment at clone time (or after clone time)
* Manage branches
* Manage worktrees
* Set and invoke commands

git-project is intended to make switching between active 'tasks' in a repository
simple and fast, without losing the progress context of existing tasks.  For
example the core plugins set up build environments such that switching among
projects and worktrees does not result in "rebuilding the world."  Builds can be
configured to invoke complex commands via a convenient name (e.g. ``git
<project> build debug``)

Substitution variables
======================

Commands that allow substitution take a form ``{varname}`` in their configured
textual representation and substitute it with the value of ``varname``.
``varname`` can be any configured value under ``<project>``, for example::

    [project]
        myvar = value

``git-project`` has several built-in substitution variables that various
commands and plugins can use:

``branch``
    The name of the currently checked-out branch
``gitdir``
    The value of ``GITDIR``
``git_common_dir``
    The value of ``GIT_COMMON_DIR``
``project``
    The value of ``<project>``

License
=======
`git-project` is distributed under the terms of the `GNU General Public License v3.0 or later`_.

.. _`GNU General Public License v3.0 or later`: https://spdx.org/licenses/GPL-3.0-or-later.html

"""

from .commandline import parse_arguments, add_top_level_command
from .commandline import get_or_add_top_level_command
from .configobj import ConfigObject
from .exception import GitProjectException
from .git import Git
from .gitproject import GitProject
from .main import main_impl
from .parsermanager import ParserManager
from .plugin import Plugin
from .pluginmanager import PluginManager
from .project import Project
from .runnable import RunnableConfigObject
from .scopedobj import ScopedConfigObject
from .substitutable import SubstitutableConfigObject
from .shell import run_command_with_shell, iter_command, capture_command
