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

import os

import git_project
from pathlib import Path
import shutil

def test_gitproject_get(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    gp = git_project.GitProject.get(git)

    projects = [name for name in gp.iternames()]

    assert projects == []

def test_gitproject_iternames(reset_directory, local_repository):
    # Gets to GITDIR
    os.chdir(local_repository.path)

    git = git_project.Git()

    gp = git_project.GitProject.get(git)

    gp.add_item('name', 'new')
    gp.add_item('name', 'test')

    projects = {name for name in gp.iternames()}

    assert projects == {'test', 'new'}
