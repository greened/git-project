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

class ConfigObjectItem:
    """A class representing a key:value pair in a git config section.  Each instance
       includes the key of the item, a default value (or None if no default)
       used to initialize the key:value pair in the section and a description
       displayed as part of the help text for commands using this key:value
       pair.

    """
    def __init__(self, key, default, description):
        self._key = key
        self._default = default
        self._description = description

    @property
    def key(self):
        """Return the key for this item."""
        return self._key

    @property
    def default(self):
        """Return the default value for this item or None if there is no deault."""
        return self._default

    @property
    def description(self):
        """Return the help text for this item."""
        return self._description
