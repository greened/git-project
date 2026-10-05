#!/usr/bin/env python3
#
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

"""Fixtures for testing git-project and its plugins.

Run git-project's tests with one of these::

  hatch run test
  hatch run cov
  hatch run all:test

``cov`` adds a coverage report. ``all`` runs the suite under each Python
version in its matrix.

Set ``GIT_CONFIG_GLOBAL=/dev/null`` and ``GIT_CONFIG_NOSYSTEM=1`` when you
run the tests. The tests make throwaway repositories and commits, and a
hook or setting in your own git config would otherwise act on them.

A test for a bug fix should fail before the fix. Check that it does.
"""

from .common import check_config_file
from .common import ParserManagerMock
from .common import PluginMock
from .common import orig_repository
from .common import remote_repository
from .common import local_repository
from .common import reset_directory
from .common import parser_manager
from .common import plugin_manager
from .common import git
from .common import bare_git
from .common import gitproject
from .common import git_project_runner
from .common import project
