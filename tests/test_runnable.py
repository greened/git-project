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

import os

import git_project
from pathlib import Path
import shutil

class MyRunnable(git_project.RunnableConfigObject):
    def __init__(self,
                 git,
                 project_section,
                 subsection,
                 ident,
                 **kwargs):
        super().__init__(git,
                         project_section,
                         subsection,
                         ident,
                         **kwargs)

    @classmethod
    def get(cls, git, project_section, ident):
        return super().get(git,
                           project_section,
                           'myrunnable',
                           ident,
                           command='cd {builddir}/{branch} && make {target}',
                           description='Test command')

    @staticmethod
    def substitutions():
        return [git_project.ConfigObjectItem('builddir',
                                             '/home/me/builds',
                                             'Build directory'),
                git_project.ConfigObjectItem('target', 'debug', 'Build target')]

def test_get(reset_directory, git):
    runnable = MyRunnable.get(git, 'project', 'test')

    assert runnable.command == 'cd {builddir}/{branch} && make {target}'

def test_substitute_command(reset_directory, git):
    class MyProject(object):
        def __init__(self):
            self._section = 'project'
            self.builddir = '/path/to/build'
            self.target = 'debug'

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()

    clargs = dict()

    command = runnable.substitute_command(git, project, clargs)

    assert command == f'cd {project.builddir}/{git.get_current_branch()} && make {project.target}'
