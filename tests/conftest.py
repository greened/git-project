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

from git_project.test_support import (
    bare_git,
    git,
    git_project_runner,
    gitproject,
    local_repository,
    orig_repository,
    parser_manager,
    plugin_manager,
    project,
    remote_repository,
    reset_directory,
)

# pytest registers the fixtures imported here. __all__ marks them as used.
__all__ = [
    "bare_git",
    "git",
    "git_project_runner",
    "gitproject",
    "local_repository",
    "orig_repository",
    "parser_manager",
    "plugin_manager",
    "project",
    "remote_repository",
    "reset_directory",
]
