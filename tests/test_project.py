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

def test_get_no_repository(reset_directory):
    git = git_project.Git()

    assert not git.has_repo()

    project = git_project.Project.get(git, 'project')

    assert not hasattr(project, 'remote')
    assert not hasattr(project, 'branch')
    assert not hasattr(project, 'builddir')
    assert not hasattr(project, 'prefix')
    assert not hasattr(project, 'sharedir')
    assert not hasattr(project, 'configure')
    assert not hasattr(project, 'build')
    assert not hasattr(project, 'install')

def test_get_in_repository(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    project = git_project.Project.get(git, 'project')

    assert project.remote == 'origin'
    assert project.branch == 'master'
    assert not hasattr(project, 'builddir')
    assert not hasattr(project, 'prefix')
    assert not hasattr(project, 'sharedir')
    assert not hasattr(project, 'configure')
    assert not hasattr(project, 'build')
    assert not hasattr(project, 'install')

def test_add_remote(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    project = git_project.Project.get(git, 'project')

    remotes = {remote for remote in project.iterremotes()}

    assert remotes == {'origin'}

    project.add_remote('upstream')

    remotes = {remote for remote in project.iterremotes()}

    assert remotes == {'origin', 'upstream'}

def test_add_branch(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    project = git_project.Project.get(git, 'project')

    branches = {branch for branch in project.iterbranches()}

    assert branches == {'master'}

    project.add_branch('project')

    branches = {branch for branch in project.iterbranches()}

    assert branches == {'master', 'project'}

def test_iterrefnames(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    project = git_project.Project.get(git, 'project')

    project.add_branch('pushed')

    branches = {branch for branch in project.iterbranches()}

    assert branches == {'master', 'pushed'}

    remotes = {remote for remote in project.iterremotes()}

    assert remotes == {'origin'}

    refs = {ref for ref in project.iterrefnames()}

    assert refs == {'refs/heads/master',
                    'refs/remotes/origin/master',
                    'refs/heads/pushed',
                    'refs/remotes/origin/pushed'}

def test_branch_is_merged(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    project = git_project.Project.get(git, 'project')

    assert project.branch_is_merged('master')
    assert not project.branch_is_merged('pushed')
    assert not project.branch_is_merged('notpushed')
    assert project.branch_is_merged('merged_remote')
    assert project.branch_is_merged('merged_local')
    assert not project.branch_is_merged('unmerged')

def test_branch_is_pushed(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    project = git_project.Project.get(git, 'project')

    assert not project.branch_is_pushed('master')
    assert project.branch_is_pushed('pushed')
    assert not project.branch_is_pushed('notpushed')
    assert project.branch_is_pushed('merged_remote')
    assert not project.branch_is_pushed('merged_local')
    assert not project.branch_is_pushed('unmerged')

def test_prune_branch(reset_directory, remote_repository, tmp_path_factory):
    remotedir = tmp_path_factory.mktemp('remote-workdir')

    os.chdir(remotedir)

    git_project.Git.capture_command(f'git clone --mirror {remote_repository.path}')

    print(f'remote.path: {remote_repository.path}')

    remote_name = Path(remote_repository.path).name + '.git'

    remote_path = str(Path.cwd() / remote_name)

    print(f'remote_path: {remote_path}')

    localdir = tmp_path_factory.mktemp('local-workdir')

    os.chdir(localdir)

    git = git_project.Git()
    project = git_project.Project.get(git, 'project')

    path = git.clone(remote_path)

    os.chdir(path)

    git = git_project.Git()

    project = git_project.Project.get(git, 'project')

    assert project._git.remote_branch_exists('pushed', 'origin')

    project.prune_branch('pushed')

    assert not project._git.remote_branch_exists('pushed', 'origin')
