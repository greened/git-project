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

from .substitutable import SubstitutableConfigObject
from .shell import run_command_with_shell

class RunnableConfigObject(SubstitutableConfigObject):
    """Base class for objects that use git-config as a backing store and act as
    command launchers.  Inherits from SubstitutableConfigObject.

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

    def substitute_command(self, git, project, formats=dict()):
        """Given a project, perform variable substitution on the command and return the
        result as a string.

        git: An object to query the repository and make config changes.

        project: The currently active Project.

        """
        return self.substitute_value(git, project, self.command, formats)

    def run(self, git, project, formats=dict()):
        """Do variable substitution and run the resulting command.

        git: An object to query the repository and make config changes.

        project: The currently active Project.

        """
        command = self.substitute_command(git, project, formats)

        print(command)

        run_command_with_shell(command)
