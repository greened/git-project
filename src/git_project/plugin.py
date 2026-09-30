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

"""Writing a git-project plugin.

git-project provides no commands of its own. A plugin adds them. This guide
covers what a plugin author needs. The run lifecycle is in git_project.main.

Registering a plugin
====================

A plugin is a subclass of Plugin. git-project finds it through the
``git-project.plugins`` entry point group, so the package that holds it
declares it in its ``pyproject.toml``::

  [project.entry-points."git-project.plugins"]
  hello = "my_package.hello:HelloPlugin"

git-project builds each plugin with no arguments, so ``__init__`` takes none
and passes a name to ``Plugin.__init__``.

A minimal plugin
================

This plugin adds ``git <project> hello <who>``::

  from git_project import Plugin, add_top_level_command

  def command_hello(git, gitproject, project, clargs):
      print(f'{project.get_section()}: hello, {clargs.who}')
      return 0

  class HelloPlugin(Plugin):
      '''The hello command prints a greeting.

      Summary::

        git <project> hello <who>

      '''
      def __init__(self):
          super().__init__('hello')

      def add_arguments(self, git, gitproject, project, parser_manager,
                        plugin_manager):
          parser = add_top_level_command(parser_manager, 'hello', 'hello',
                                         help='Say hello')
          parser.add_argument('who', help='Who to greet')
          parser.set_defaults(func=command_hello)

The init plugin in git-project-core-plugins is a real plugin this small.

Hooks
=====

git-project calls each plugin's hooks in this order, and each hook for every
plugin before the next hook:

#. ``add_class_hooks``, right after the plugins load. Change classes here.
   The active Project already exists, and the GitProject is built after
   this hook.
#. ``add_arguments``. Add commands and options.
#. ``modify_arguments``. Change what other plugins added.
#. The command line is parsed.
#. ``initialize``. Set up state, such as pushing a scope.
#. The chosen command's function runs.

Plugins run in the order Python's entry point lookup returns them, which no
plugin chooses. So a plugin cannot rely on another plugin's
``add_arguments`` having run before its own. Anything that touches another
plugin's command belongs in ``modify_arguments``.

Commands
========

``add_top_level_command(parser_manager, name, key)`` adds a command. name is
what the user types. key names the parser inside git-project and must be
unique across all plugins. A command's function is set with
``parser.set_defaults(func=...)``. git-project calls it as
``func(git, gitproject, project, clargs)``, where gitproject is the
GitProject for the repository, project is the active Project and clargs is
the parsed command line. An int return is the exit status. Any other return
exits with 0.

A plugin extends another plugin's command in ``modify_arguments``. Find its
parser by key with ``parser_manager.find_parser(key)``, add options to it,
and wrap its function::

  parser = parser_manager.find_parser('clone')
  if parser:
      original = parser.get_default('func')

      def command_clone(git, gitproject, project, clargs):
          result = original(git, gitproject, project, clargs)
          # Do more here.
          return result

      parser.set_defaults(func=command_clone)

The worktree plugin in git-project-core-plugins wraps clone and init this
way.

Configuration
=============

A plugin keeps its settings in config objects: see git_project.configobj.
Derive from ConfigObject, or from ScopedConfigObject,
SubstitutableConfigObject or RunnableConfigObject for scopes, substitution
or a command to run. The core plugins give each class a ``subsection()``
staticmethod and a ``get(git, project, ...)`` classmethod that passes it on,
so the class, not its callers, knows where its section lives.

To add a scope, push an object onto the project in ``initialize``, or in the
class's ``get``, with ``project.push_scope``. See git_project.scopedobj.

``iterclasses`` yields a plugin's config classes, so that other plugins can
find them. The config plugin in git-project-core-plugins uses it to give
each class a config subcommand.

Help and errors
===============

A plugin's class docstring is its manual. ``manpage`` returns it, and the
help plugin in git-project-core-plugins shows it for
``git <project> help <command>``.

For a failure the user can act on, raise GitProjectException. git-project
prints its message and exits with a failure status.

Testing
=======

``git_project.test_support`` provides pytest fixtures, such as ``git``,
``project``, ``parser_manager`` and ``reset_directory``. Import the ones a
test needs into its ``conftest.py``. Run tests with
``GIT_CONFIG_GLOBAL=/dev/null``, so that your own git config cannot change
the result.

"""

from abc import ABC, abstractmethod

class Plugin(ABC):
    """The base class for all plugins. Plugins should inherit from this and
    implement add_arguments to register any command-line commands and options
    they may need. See the module documentation for the hooks and the order
    they run in.

    """
    def __init__(self, name):
        self.name = name
        pass

    def manpage(self):
        """Return this plugin's manual, its class docstring."""
        return self.__doc__

    def initialize(self, git, gitproject, project, plugin_manager):
        """Run initialization code for the plugin. git-project calls it after the
        command line is parsed and before the command runs.

        git: A Git object to examine the repository.

        gitproject: The GitProject, the config that is not tied to a project.

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

        gitproject: The GitProject, the config that is not tied to a project.

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

        gitproject: The GitProject, the config that is not tied to a project.

        project: The currently-active project.

        parser_manager: A ParserManager object used to register options and
                        subparsers.

        plugin_manager: A PluginManager object used to query plugins.


        """
        pass

    def add_class_hooks(self, git, project, plugin_manager):
        """Add any class hooks this plugin needs. These hooks apply to class objects.
        Hooks can be anything at all, for example adding class members or
        enhancing existing properties. git-project calls it right after the
        plugins load. The active Project already exists at that point.

        git: A Git object to examine the repository.

        project: The active Project.

        plugin_manager: A PluginManager object used to query plugins.

        """
        pass

    def iterclasses(self):
        """Iterate over any public classes in this plugin.  Public classes are assumed
        to be modifiable by other plugins.

        """
        return
        yield
