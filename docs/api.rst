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
    FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
    more details.

..
    You should have received a copy of the GNU Affero General Public License
    along with git-project. If not, see <https://www.gnu.org/licenses/>.

API reference
=============

.. currentmodule:: git_project

Configuration objects
---------------------

.. autoclass:: ConfigObject
   :members:

.. autoclass:: ScopedConfigObject
   :members:

.. autoclass:: SubstitutableConfigObject
   :members:

.. autoclass:: RunnableConfigObject
   :members:

Projects
--------

.. autoclass:: Project
   :members:

.. autoclass:: GitProject
   :members:

Plugins and the command line
----------------------------

.. autoclass:: Plugin
   :members:

.. autoclass:: PluginManager
   :members:

.. autoclass:: ParserManager
   :members:

.. autofunction:: add_top_level_command

.. autofunction:: get_or_add_top_level_command

.. autofunction:: parse_arguments

.. autofunction:: main_impl

Git
---

.. autoclass:: Git
   :members:

Shell commands
--------------

.. autofunction:: run_command_with_shell

.. autofunction:: iter_command

.. autofunction:: capture_command

Errors
------

.. autoclass:: GitProjectException
