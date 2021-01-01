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

import git_project
from git_project.test_support import check_config_file

import os
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

def test_runnable_get(reset_directory, git):
    runnable = MyRunnable.get(git, 'project', 'test')

    assert runnable.command == 'cd {builddir}/{branch} && make {target}'

def test_runnable_substitute_command(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             None,
                             'myproject',
                             builddir='/path/to/build',
                             target='debug')

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()

    clargs = dict()

    command = runnable.substitute_command(git, project)

    assert command == f'cd {project.builddir}/{git.get_current_branch()} && make {project.target}'

def test_runnable_substitute_command_recursive(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             None,
                             'myproject',
                             builddir='/path/to/build/{target}',
                             target='debug')

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()

    clargs = dict()

    command = runnable.substitute_command(git, project)

    assert command == f'cd /path/to/build/{project.target}/{git.get_current_branch()} && make {project.target}'

def test_runnable_substitute_command_no_dup(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             None,
                             'myproject',
                             builddir='/path/to/build/{target}',
                             target='install')

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()

    project.build = 'devrel'
    project.add_item('build', 'check-devrel')

    check_config_file('project.myproject',
                      'builddir',
                      {'/path/to/build/{target}'})

    check_config_file('project.myproject',
                      'target',
                      {'install'})

    check_config_file('project.myproject',
                      'build',
                      {'devrel', 'check-devrel'})

    command = runnable.substitute_command(git, project)

    assert command == f'cd /path/to/build/{project.target}/{git.get_current_branch()} && make {project.target}'

    check_config_file('project.myproject',
                      'builddir',
                      {'/path/to/build/{target}'})

    check_config_file('project.myproject',
                      'target',
                      {'install'})

    check_config_file('project.myproject',
                      'build',
                      {'devrel', 'check-devrel'})

def test_runnable_run_no_dup(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             None,
                             'myproject',
                             builddir='/path/to/build/{target}',
                             target='install')

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()

    project.build = 'devrel'
    project.add_item('build', 'check-devrel')

    check_config_file('project.myproject',
                      'builddir',
                      {'/path/to/build/{target}'})

    check_config_file('project.myproject',
                      'target',
                      {'install'})

    check_config_file('project.myproject',
                      'build',
                      {'devrel', 'check-devrel'})

    clargs = dict()

    runnable.run(git, project, clargs)

    check_config_file('project.myproject',
                      'builddir',
                      {'/path/to/build/{target}'})

    check_config_file('project.myproject',
                      'target',
                      {'install'})

    check_config_file('project.myproject',
                      'build',
                      {'devrel', 'check-devrel'})

def test_runnable_substitute_command_subsection(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             None,
                             'myproject',
                             builddir='/path/to/build',
                             target='{myrunnable}')

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()

    project.myrunnable = 'test'

    command = runnable.substitute_command(git, project)

    assert command == f'cd {project.builddir}/{git.get_current_branch()} && make {project.myrunnable}'

def test_runnable_substitute_project(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             None,
                             'myproject',
                             builddir='/path/to/build',
                             target='{myrunnable} {project}')

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()

    project.myrunnable = 'test'

    command = runnable.substitute_command(git, project)

    assert command == f'cd {project.builddir}/{git.get_current_branch()} && make {project.myrunnable} {project.get_section()}'

def test_runnable_substitute_scope(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             None,
                             'myproject',
                             builddir='/path/to/build/{worktree}',
                             target='{myrunnable} {project}')

    class MyWorktree(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git,
                             'project',
                             'worktree',
                             'myworktree')

    runnable = MyRunnable.get(git, 'project', 'test')

    project = MyProject()
    worktree = MyWorktree()

    project.push_scope(worktree)

    project.myrunnable = 'test'

    command = runnable.substitute_command(git, project)

    assert command == f'cd /path/to/build/myworktree/{git.get_current_branch()} && make {project.myrunnable} {project.get_section()}'
