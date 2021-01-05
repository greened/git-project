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
"""git-project: Manage project work.

Summary:

git project <command> [<options>]

Commands are registered by plugins and show with 'git project --help.'  Each
command also has a --help option to explore workings of th command.

Users may link to git-project with a name appropriate to the project (for
example, git-fizzbin to invoke as 'git fizzbin <command> [<options>]).
git-project will then place all configuration in a section named after the link
('fizzbin' in this case).  This way one may have multiple projects active in a
single repository by invoking git-project via various links.

"""

import argparse
import getpass
import io
import os
from pathlib import Path
import pygit2
import re
import shlex
import subprocess
import sys
import urllib.parse

try:
    from importlib import metadata
except ImportError:
    # Running on pre-3.8 Python; use importlib-metadata package
    import importlib_metadata as metadata

from .parsermanager import ParserManager

def get_version_string(package):
    version = metadata.version(package)

    return f'{package} version {version}'

def add_version_argument(parser, package):
    parser.add_argument('--version',
                        action='version',
                        version=get_version_string(package),
                        help='Print version')

def parse_arguments(git, gitproject, project, plugin_manager, args):
    """Register plugin comand-line arguments.  Parse command-link arguments and
    invoke command functions.

    git: Git object to examine the repository.

    gitproject: GitProject object to provide cross-project configuration.

    project: Project object to provide project-specific configuration.

    plugin_manager: A manager holding available plugins.

    """
    parser_manager = ParserManager(gitproject, project)

    parser = parser_manager.find_parser('__main__')

    # --version
    add_version_argument(parser, 'git-project')

    command_subparser = parser_manager.add_subparser(parser,
                                                     'command',
                                                     dest='command',
                                                     help='commands')
    command_subparser.required = True

    for plugin in plugin_manager.iterplugins():
        plugin.add_arguments(git,
                             gitproject,
                             project,
                             parser_manager,
                             plugin_manager)

    # Once all plugins have added arguments, give them a chance to modify
    # arguments other plugsin may have added.
    for plugin in plugin_manager.iterplugins():
        plugin.modify_arguments(git,
                                gitproject,
                                project,
                                parser_manager,
                                plugin_manager)

    clargs = parser_manager.parse_args(args)

    if not hasattr(clargs, 'func'):
        parser_manager.error()
        sys.exit(1)

    return clargs

def add_top_level_command(parser_manager,
                          name,
                          key,
                          **kwargs):
    """Create a top-level command.  Throw an exception if the command already
    exists.

    parser_manager - The active ParserManager.

    name - The name of the command to be invoked.

    key - A unique identifier for the created parser.

    kwargs - Passthrough to argparse parser.

    """

    command_subparser = parser_manager.find_subparser('command')
    assert command_subparser
    parser = parser_manager.add_parser(command_subparser,
                                       name,
                                       key,
                                       **kwargs)

    return parser

def get_or_add_top_level_command(parser_manager,
                                 name,
                                 key,
                                 **kwargs):
    """Retrieve a top-level command parser or create one if none exists.

    parser_manager - The active ParserManager.

    name - The name of the command to be invoked.

    key - A unique identifier for the created parser.

    kwargs - Passthrough to argparse parser.

    """

    parser = parser_manager.find_parser(key)
    if not parser:
        parser = add_top_level_command(parser_manager,
                                       name,
                                       key,
                                       **kwargs)
    return parser
