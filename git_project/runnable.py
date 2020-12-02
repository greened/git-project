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

from pathlib import Path

from .configobj import ConfigObject
from .shell import run_command_with_shell

class RunnableConfigObject(ConfigObject):
    """Base class for objects that use git-config as a backing store and act as
    command launchers.  Inherits from ConfigObject.

    Derived classes should implement the ConfigObject protocol.

    """
    def __init__(self, git, section, subsection, ident, **kwargs):
        """RunnableConfigObject construction.  This should be treated as a private
        method and all construction should occur through the get method.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        super().__init__(git, section, subsection, ident, **kwargs)

    def substitute_command(self, git, project, clargs):
        """Given a project, perform variable substitution on the object's command and
        return the result as a string.

        git: An object to query the repository and make config changes.

        project: The currently active Project.

        """
        command = self.command

        formats = dict()

        found_path = False
        for key, value in project.iteritems():
            if key == 'path':
                found_path = True
            formats[key] = value

        if not found_path:
            # We haven't found a worktree or other construct to give us a path,
            # so do a mildly expensive thing to get the path of the curernt
            # working copy.
            path = git.get_working_copy_root()
            formats['path'] = path

        formats['branch'] = git.get_current_branch()

        while True:
            newcommand = command.format(**formats)
            changed = False if newcommand == command else True
            command = newcommand
            if not changed:
                break

        return command

    def run(self, git, project, clargs):
        """Do variable substitution and run the resulting command.

        git: An object to query the repository and make config changes.

        project: The currently active Project.

        """
        command = self.substitute_command(git, project, clargs)

        print(command)

        run_command_with_shell(command)
