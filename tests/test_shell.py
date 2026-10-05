#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2020-present David A. Greene <dag@obbligato.org>

# SPDX-License-Identifier: AGPL-3.0-or-later

# Copyright 2020 David A. Greene

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

import pytest

import git_project


def test_run_command_with_shell_returns_zero_on_success():
    assert git_project.run_command_with_shell("true") == 0


def test_run_command_with_shell_returns_nonzero_on_failure():
    assert git_project.run_command_with_shell("false") != 0


def test_run_command_with_shell_dry_run_returns_zero():
    assert git_project.run_command_with_shell("false", dry_run=True) == 0


def test_iter_command_yields_lines():
    assert list(git_project.iter_command('printf "a\\nb\\n"')) == [
        "a\n",
        "b\n",
    ]


def test_iter_command_failure_reports_status_and_stderr():
    with pytest.raises(Exception, match="exited with code 3") as info:
        list(git_project.iter_command('sh -c "echo oops >&2; exit 3"'))
    assert "oops" in str(info.value)


def test_capture_command_takes_a_list():
    assert git_project.capture_command(["printf", "%s", "a b"]) == b"a b"
