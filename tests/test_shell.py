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

def test_run_command_with_shell_returns_zero_on_success():
    assert git_project.run_command_with_shell("true") == 0

def test_run_command_with_shell_returns_nonzero_on_failure():
    assert git_project.run_command_with_shell("false") != 0

def test_run_command_with_shell_dry_run_returns_zero():
    assert git_project.run_command_with_shell("false", dry_run=True) == 0
