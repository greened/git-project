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
    FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
    more details.

..
    You should have received a copy of the GNU Affero General Public License
    along with git-project. If not, see <https://www.gnu.org/licenses/>.

ChangeLog
=========
`Unreleased`_
-------------

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

.. _Unreleased: https://github.com/greened/git-project/compare/v0.0.38...HEAD
.. _0.0.38: https://github.com/greened/git-project/compare/v0.0.37...v0.0.38
