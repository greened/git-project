..
    SPDX-FileCopyrightText: 2023-present David A. Greene <dag@obbligato.org>

..
    SPDX-License-Identifier: AGPL-3.0-or-later

..
    Copyright 2023 David A. Greene

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

ChangeLog
=========
`Unreleased`_
-------------
Added
.....
- ``capture_command`` takes a list of arguments as well as a string.

Fixed
.....
- ``substitute_value``, ``substitute_command`` and ``run`` shared one
  default ``formats`` dict across calls, and ``substitute_value`` added its
  names to it. So within one process, an object could resolve a name it does
  not define to another object's value. Each call now works on its own copy,
  and a ``formats`` dict passed in is no longer changed.
- Removing one value of a config key failed when the value held a space.
  It was split into several arguments to ``git config --unset``. The pattern
  now reaches git as given, so a pattern escaped twice to get through that
  split must be escaped once.
- ``Git.get_git_common_dir`` returns an absolute path in a worktree that plain
  ``git worktree add`` made. It returned the relative path that git writes, so
  ``{git_common_dir}`` substituted ``../..`` there.

`0.0.39`_ - 2026-09-30
----------------------
Added
.....
- A guide to writing plugins, in the ``git_project.plugin`` module
  documentation, with the run lifecycle in ``git_project.main``.
- A guide to working on git-project itself, in the ``git_project._contributing``
  module documentation.

Changed
.......
- The PyPI description now ends with the newest release's changelog section
  and a link to the full changelog.
- ``git <project> -h`` now opens with a summary of git-project and of how the
  link name selects a project. It showed only the usage and the arguments
  before.
- The package description is rewritten. It now explains projects,
  configuration, scopes and substitution, and it warns that a substituted
  value is evaluated as Python. It also says to ask for help with
  ``git <project> -h``, because git sends ``git <project> --help`` to a man
  page.

Fixed
.....
- The package description named the GNU General Public License. git-project
  is licensed under the GNU Affero General Public License v3.0 or later, as
  its source headers and ``pyproject.toml`` already said.
- The package description now says how to create the ``git-<project>`` link
  that selects a project.
- ``ScopedConfigObject.get_scope`` found only the topmost scope. With more
  than one scope pushed, a lower scope was never found, so a ``{name}``
  substitution naming it could not be resolved.
- ``ParserManager.get_or_add_parser`` passed its name and key to
  ``add_parser`` in the wrong order. A parser it created was registered under
  the name and shown to the user as the key.
- A project whose name contains ``.`` or ``_``, such as one run through a
  ``git-fizz_bin`` link, lost its settings between runs. Its values were
  written to the ``fizz-bin`` section but read back from ``fizz_bin``.
- ``iter_command`` raised ``NameError`` instead of running. Its exit check
  read the status before the process had finished and then named two
  variables that do not exist. It now waits for the command, and a failure
  reports the exit status and the command's standard error.

`0.0.38`_ - 2026-09-24
----------------------
Added
.....
- ``prune_branch`` takes a ``keep_remote_branch`` keyword. It previously
  deleted the branch from every project remote as well as locally, so retiring
  a local branch destroyed the remote copy with it.

Changed
.......
- Python 3.10 or later is now required. ``list_heads`` needs it, and 1.15.1 is
  the last pygit2 that supports 3.9, so on 3.9 there is no installable pygit2
  carrying the API.
- pygit2 1.18.2 or later is now required, up from 1.15.1. The old range still
  resolved, so the package installed cleanly and then raised ``AttributeError``
  in use.

Fixed
.....
- ``git <project> clone`` did not work at all. ``Git.clone`` required an ssh ID,
  so the clone paths raised ``TypeError``. The ID is now optional, and a
  keypair is simply not offered when there is none. This also fixes
  ``fetch_remote``, ``remote_branch_exists`` and ``delete_remote_branch`` for
  any repository that never set ``ssh.id``.
- ``remote_branch_exists`` called ``Remote.ls_remotes()``, which pygit2 1.20
  removed. It now calls ``list_heads()`` and reads the fields off the
  ``RemoteHead`` objects.
- A ``Git`` re-pointed at a path with no repository stayed attached to the
  previous one. ``has_repo`` answered ``True``, so later work ran against the
  repository the caller had left. It now detaches, and ``has_repo`` answers
  ``False``.
- A ``Git`` built outside any repository named a missing private field rather
  than the real fault. ``reinit`` set the repository only when discovery
  succeeded, so most accessors raised ``AttributeError``. ``config`` named
  ``_config`` rather than ``_repo``, and ``committish_exists`` raised nothing
  at all and answered ``False``, which said the committish was absent. The
  repository accessors now raise ``GitProjectException`` naming the path that
  was searched.
- The Issues link on the PyPI project page returned 404. The URL named
  ``unknown/greened`` instead of ``greened/git-project``, a leftover from
  hatch's project template.
- The PyPI long description stopped at the separator after the badges, so
  everything from Installation on went unpublished. A second readme fragment
  now carries the rest.
- The Sphinx docs rendered no module documentation at all. ``automodule`` was
  asked for ``git-project``, which is not an importable name; it now asks for
  ``git_project``. No declared environment supplied Sphinx either, so a
  ``docs`` environment with Sphinx is now declared.

.. _Unreleased: https://github.com/greened/git-project/compare/v0.0.39...HEAD
.. _0.0.39: https://github.com/greened/git-project/compare/v0.0.38...v0.0.39
.. _0.0.38: https://github.com/greened/git-project/compare/v0.0.37...v0.0.38
