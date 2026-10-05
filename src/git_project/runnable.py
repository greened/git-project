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

"""Config objects that run a command.

A runnable config object has a ``command`` item. ``run`` substitutes it,
prints the result, runs it through the shell and returns the shell's exit
status. The run plugin in git-project-core-plugins builds a runnable class
for each run alias, such as ``build``.

"""

from .shell import run_command_with_shell
from .substitutable import SubstitutableConfigObject


class RunnableConfigObject(SubstitutableConfigObject):
    """Base class for objects that use git-config as a backing store and act as
    command launchers.  Inherits from SubstitutableConfigObject.

    Derived classes should implement the ConfigObject protocol.

    """

    def __init__(self, git, section, subsection, ident, **kwargs):
        """RunnableConfigObject construction.  This should be treated as a private
        method and all construction should occur through the get method.

        git: An object to query the repository and make config changes.

        section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to section

        ident: The name of this specific ConfigObject.

        kwargs: Keyword arguments of property values to set upon construction.

        """
        super().__init__(git, section, subsection, ident, **kwargs)

    def substitute_command(self, git, project, formats=None):
        """Given a project, perform variable substitution on the command and return the
        result as a string.

        git: An object to query the repository and make config changes.

        project: The currently active Project.

        """
        return self.substitute_value(git, project, self.command, formats)

    def run(self, git, project, formats=None):
        """Do variable substitution, print the command and run it through the shell.
        Return the shell's exit status.

        git: An object to query the repository and make config changes.

        project: The currently active Project.

        formats: Extra names for substitution. See substitute_value.

        """
        command = self.substitute_command(git, project, formats)

        print(command)

        return run_command_with_shell(command)
