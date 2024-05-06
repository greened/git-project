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
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License along
# with git-project. If not, see <https://www.gnu.org/licenses/>.

import contextlib
import os
from pathlib import Path
import pygit2
import pytest

from git_project.test_support import check_config_file
from git_project.test_support import git_project_runner
from git_project.test_support import orig_repository
from git_project.test_support import remote_repository
from git_project.test_support import local_repository
from git_project.test_support import reset_directory
from git_project.test_support import parser_manager
from git_project.test_support import plugin_manager
from git_project.test_support import git
from git_project.test_support import bare_git
from git_project.test_support import gitproject
from git_project.test_support import project
