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

"""The git-project run lifecycle.

main runs git-project and turns the result into an exit status. main_impl
does the work, in this order:

#. Find the repository from the current directory, and check the config
   file for repeated entries.
#. Take the active project's name from the program name, with any ``git-``
   prefix removed.
#. Build the active Project.
#. Load the plugins and call each one's ``add_class_hooks``, which receives
   the project.
#. Build the GitProject, now that the class hooks are in place.
#. Parse the command line. Every plugin's ``add_arguments`` runs, then every
   plugin's ``modify_arguments``. See git_project.commandline.
#. Call each plugin's ``initialize``.
#. Call the chosen command's ``func(git, gitproject, project, clargs)``.
#. Check the config file again, and return what ``func`` returned.

main exits with that value when it is an int, and with 0 otherwise. A
GitProjectException prints its message and exits with a failure status. See
git_project.plugin for what a plugin does at each step.

"""

import sys
from pathlib import Path

import git_project


def main_impl(args=None):
    """The main entry point for the git-config tools."""

    if not args:
        args = sys.argv[1:]

    git = git_project.Git()

    git.validate_config()

    project_name = Path(sys.argv[0]).name

    prefix = "git-"
    if project_name.startswith(prefix):
        project_name = project_name[len(prefix) :]

    plugin_manager = git_project.PluginManager()

    project = git_project.Project.get(git, project_name)

    plugin_manager.load_plugins(git, project)

    # Now that class hooks have been added, instantiate objects.
    gp = git_project.GitProject.get(git)

    clargs = git_project.parse_arguments(
        git, gp, project, plugin_manager, args
    )

    plugin_manager.initialize_plugins(git, gp, project)

    rc = clargs.func(git, gp, project, clargs)

    git.validate_config()

    return rc


def main(args=None):
    try:
        rc = main_impl(args)
        # Only an int return is an exit code; command funcs may return a
        # domain object (e.g. the created Worktree), which must not turn a
        # successful run into a non-zero process exit.
        raise SystemExit(rc if isinstance(rc, int) else 0)
    except git_project.GitProjectException as exception:
        print(f"{exception.message}")
        raise SystemExit(-1) from None
