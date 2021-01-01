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

from abc import ABC, abstractmethod

class Plugin(ABC):
    """The base class for all plugins.  Plugins should inherit from this and
    implement add_arguments to register any command-line commands and options
    they may need.

    """
    def __init__(self, name):
        self.name = name
        pass

    def manpage(self):
        return self.__doc__

    def initialize(self, git, gitproject, project, plugin_manager):
        """Run initialization code for the plugin.

        git: A Git object to examine the repository.

        gitproject: A GitProject object to explore and manipulate the active
                    project.

        project: The active Project.

        plugin_manager: The active  PluginManager.

        """
        pass

    @abstractmethod
    def add_arguments(self,
                      git,
                      gitproject,
                      project,
                      parser_manager,
                      plugin_manager):
        """Add arguments and subparsers for plugins.

        git: A Git object to examine the repository.

        gitproject: A GitProject object to explore and manipulate the active
                    project.

        project: The currently-active project.

        parser_manager: A ParserManager object used to register options and
                        subparsers.

        plugin_manager: A PluginManager object used to query plugins.

        Plugins may query the parser_manager for a top-level argparse-style
        subparser called 'command' to register new commands.  Each new command
        should have its own parser which can be used to provide command-level
        options.  Plugins may also register new top-level options if they wish.

        """

    def modify_arguments(self,
                         git,
                         gitproject,
                         project,
                         parser_manager,
                         plugin_manager):
        """Alter any existing arguments.  With this method a plugin could, for example,
        update a command function to do a bit of work before and/or after the
        original command is run, or even replace existing command logic
        entirely.

        git: A Git object to examine the repository.

        gitproject: A GitProject object to explore and manipulate the active
                    project.

        project: The currently-active project.

        parser_manager: A ParserManager object used to register options and
                        subparsers.

        plugin_manager: A PluginManager object used to query plugins.


        """
        pass

    def add_class_hooks(self, git, project, plugin_manager):
        """Add any class hooks this plugin needs.  These hooks apply to class objects.
        Hooks can be anything at all, for example adding class members or
        enhancing existing properties.

        """
        pass

    def iterclasses(self):
        """Iterate over any public classes in this plugin.  Public classes are assumed
        to be modifiable by other plugins.

        """
        return
        yield
