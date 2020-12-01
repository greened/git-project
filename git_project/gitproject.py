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

from .configobj import ConfigObject

class GitProject(ConfigObject):
    """Manage the global git-project config."""

    def __init__(self, git, section, subsection, ident):
        """GitProject construction.  This should be treated as a private method and all
        construction should occur through the get method.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        assert section == 'gitproject'
        assert subsection == None
        assert ident == None
        super().__init__(git, section, subsection, ident)

    @classmethod
    def get(cls, git):
        """Factory to construct a GitProject object.

        cls: The derived class being constructed.

        git: An object to query the repository and make config changes.

        """
        return super().get(git,
                           'gitproject',
                           None,
                           None)

    def iternames(self):
        """Iteratte over the configured project names."""
        for name in self.iter_multival('name'):
            yield name
