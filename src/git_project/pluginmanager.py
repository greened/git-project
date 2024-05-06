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
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License along
# with git-project. If not, see <https://www.gnu.org/licenses/>.

import sys
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

# TODO: Remove after transitioning git-project-core-plugins.
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
        plugins = entry_points(group='git-project.plugins')
        # TODO: Remove after transitioning git-project-core-plugins.
        plugins.extend([entpt for entpt in
                        pkg_resources.iter_entry_points(ENTRYPOINT)])
        for entrypoint in plugins:
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
