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


import pytest

import git_project
from git_project.test_support import check_config_file


def test_main_no_dup(reset_directory, git, project):
    project._git.validate_config()

    project._git.validate_config()
    git_project.main_impl(["config", "branch"])

    project.build = "devrel"

    project._git.validate_config()
    git_project.main_impl(["config", "branch"])

    project.add_item("build", "check-devrel")

    project._git.validate_config()
    git_project.main_impl(["config", "branch"])

    check_config_file("project", "build", {"devrel", "check-devrel"})

    project._git.validate_config()
    git_project.main_impl(["config", "branch"])

    check_config_file("project", "build", {"devrel", "check-devrel"})


def test_main_help_shows_summary(reset_directory, git, capsys):
    with pytest.raises(SystemExit):
        git_project.main_impl(["--help"])

    out = capsys.readouterr().out
    assert "git <project> <command> [<options>]" in out
    assert "The name git-project runs under selects the active project." in out


class _DefaultsPlugin(git_project.Plugin):
    """Adds 'look', which may write the defaults, and 'peek', which may not."""

    def __init__(self):
        super().__init__("defaults")
        self.branch_at_initialize = None

    def initialize(self, git, gitproject, project, plugin_manager):
        self.branch_at_initialize = project.has_item("branch")

    def add_arguments(
        self, git, gitproject, project, parser_manager, plugin_manager
    ):
        look = git_project.add_top_level_command(
            parser_manager, "look", "look"
        )
        look.set_defaults(func=lambda *args: 0)
        peek = git_project.add_top_level_command(
            parser_manager, "peek", "peek"
        )
        peek.set_defaults(func=lambda *args: 0, write_project_defaults=False)


@pytest.fixture
def defaults_plugin(monkeypatch):
    plugin = _DefaultsPlugin()

    def load_plugins(self, git, project):
        self.plugins.append(plugin)

    monkeypatch.setattr(
        git_project.PluginManager, "load_plugins", load_plugins
    )
    monkeypatch.setattr("sys.argv", ["git-project"])
    return plugin


@pytest.mark.parametrize("command, written", [("look", True), ("peek", False)])
def test_main_project_defaults(
    reset_directory, git, defaults_plugin, command, written
):
    assert not git.config.has_item("project", "branch")
    assert not git.config.has_item("project", "remote")

    git_project.main_impl([command])

    config = git_project.Git().config
    assert config.has_item("project", "branch") == written
    assert config.has_item("project", "remote") == written
    if written:
        assert config.get_item("project", "branch") == "master"
        assert config.get_item("project", "remote") == "origin"


def test_main_project_defaults_before_initialize(
    reset_directory, git, defaults_plugin
):
    assert not git.config.has_item("project", "branch")

    git_project.main_impl(["look"])

    assert defaults_plugin.branch_at_initialize is True
