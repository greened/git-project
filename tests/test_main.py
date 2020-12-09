#!/usr/bin/env python3
#
# Copyright 2020 David A. Greene
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
#


import git_project
from git_project.test_support import check_config_file

import os
from pathlib import Path
import shutil

def test_main_no_dup(reset_directory, git, project):
    project._git.validate_config()

    project._git.validate_config()
    git_project.main_impl(['config', 'branch'])

    project.build = 'devrel'

    project._git.validate_config()
    git_project.main_impl(['config', 'branch'])

    project.add_item('build', 'check-devrel')

    project._git.validate_config()
    git_project.main_impl(['config', 'branch'])

    check_config_file('project',
                      'build',
                      {'devrel', 'check-devrel'})

    project._git.validate_config()
    git_project.main_impl(['config', 'branch'])

    check_config_file('project',
                      'build',
                      {'devrel', 'check-devrel'})
