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

import pkg_resources

ENTRYPOINT = 'git_project.plugins'

class PluginManager(object):
    """A Borg class responsible for discovering plugins and providing handles to
    them.

    """
    _shared_state = {}

    def __init__(self):
        self.__dict__ = PluginManager._shared_state
        self.plugins = []

    def load_plugins(self, git, project):
        """Discover all plugins and instantiate them."""
        for entrypoint in pkg_resources.iter_entry_points(ENTRYPOINT):
            plugin_class = entrypoint.load()
            plugin = plugin_class()
            self.plugins.append(plugin)
        for plugin in self.iterplugins():
            plugin.add_class_hooks(git, project, self)

    def initialize_plugins(self, git, gitproject, project):
        """Run any plugin setup code before invoking the main command routines.  This is
        called immediately after argument parsing.

        """
        for plugin in self.iterplugins():
            plugin.initialize(git, gitproject, project, self)

    def iterplugins(self):
        """Iterate over discovered plugins, yielding an instantiated Plugin object."""
        for plugin in self.plugins:
            yield plugin
