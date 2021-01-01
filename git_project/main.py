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

import argparse
from pathlib import Path
import sys

def main_impl(args=None):
    """The main entry point for the git-config tools."""

    if not args:
        args = sys.argv[1:]

    git = git_project.Git()

    git.validate_config()

    project_name = Path(sys.argv[0]).name

    prefix = 'git-'
    if project_name.startswith(prefix):
        project_name = project_name[len(prefix):]

    plugin_manager = git_project.PluginManager()

    project = git_project.Project.get(git, project_name)

    plugin_manager.load_plugins(git, project)

    # Now that class hooks have been added, instantiate objects.
    gp = git_project.GitProject.get(git)

    clargs = git_project.parse_arguments(git, gp, project, plugin_manager, args)

    plugin_manager.initialize_plugins(git, gp, project)

    clargs.func(git, gp, project, clargs)

    git.validate_config()

def main(args=None):
    try:
        main_impl(args)
    except git_project.GitProjectException as exception:
        print(f'{exception.message}')
        raise SystemExit(-1)
