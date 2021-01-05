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

class SubstitutableConfigObject(ConfigObject):
    """Base class for objects that use git-config as a backing store and allow
    substitution of config values.  Inherits from ConfigObject.

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

    def substitute_value(self, git, project, string, formats=dict()):
        """Given a project, perform variable substitution on a string and return the
        result as a string.

        git: An object to query the repository and make config changes.

        project: The currently active Project.

        string: The string on which to perform substitution.

        """
        found_path = False
        for key, value in project.iteritems():
            if key == 'path':
                found_path = True
            if key == self.get_subsection():
                value = self.get_ident()
            formats[key] = value

        formats['project'] = project.get_section()

        if not found_path:
            # We haven't found a worktree or other construct to give us a path,
            # so do a mildly expensive thing to get the path of the curernt
            # working copy.
            path = git.get_working_copy_root()
            formats['path'] = path

        formats['branch'] = git.get_current_branch()

        while True:
            try:
                newstring = string.format(**formats)
            except KeyError as exception:
                # See if this is a scope name.
                for key in exception.args:
                    scope = project.get_scope(key)
                    if scope:
                        value = scope.get_ident()
                        formats[key] = value

                # Try again after adding scopes.
                newstring = string.format(**formats)

            changed = False if newstring == string else True
            string = newstring
            if not changed:
                break

        return string
