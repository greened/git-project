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

import contextlib
import os
from pathlib import Path
import pygit2
import pytest

class ParserManagerMock(object):
    class ParserMock(object):
        class Argument(object):
            def __init__(self, name, *args, **kwargs):
                self.name = name
                self.args = args
                self.kwargs = kwargs

            def __repr__(self):
                return f'Name:{self.name}: Args:{self.args} Kwargs:{self.kwargs}'

            def __eq__(self, other):
                if self.name != other.name:
                    return False
                if len(self.args) != len(other.args):
                    return False
                for self_arg, other_arg in zip(self.args, other.args):
                    if self_arg != other_arg:
                        return False
                if len(self.kwargs) != len(other.kwargs):
                    return False
                for self_kwarg, other_kwarg in zip(self.kwargs.items(),
                                                   other.kwargs.items()):
                    if self_kwarg[0] != other_kwarg[0]:
                        return False
                    if self_kwarg[1] != other_kwarg[1]:
                        return False
                return True

        def __init__(self, key):
            self.key = key
            self.arguments = []
            self.defaults = dict()

        def __eq__(self, other):
            if self.key != other.key:
                return False
            if len(self.arguments) != len(other.arguments):
                return False
            for self_arg, other_arg in zip(self.arguments, other.arguments):
                if self_arg != other_arg:
                    return False
            if len(self.defaults) != len(other.defaults):
                return False
            for self_default, other_default in zip(self.defaults.items(),
                                               other.defaults.items()):
                if self_defaults[0] != other_default[0]:
                    return False
                if self_defaults[1] != other_default[1]:
                    return False

        def add_argument(self, name, *args, **kwargs):
            self.arguments.append(self.Argument(name, *args, **kwargs))

        def set_defaults(self, **kwargs):
            for key, value in kwargs.items():
                self.defaults[key] = value

        def get_default(self, name):
            return self.defaults[name]

    class SubparserMock(object):
        def __init__(self, key):
            self.key = key
            self.parsers = []

    def __init__(self):
        self.parsers = dict()

    def add_subparser(self, parser, key, **kwargs):
        return self.SubparserMock(key)

    def add_parser(self, subparser, name, key, **kwargs):
        parser = self.ParserMock(key)
        self.parsers[key] = parser
        return parser

    def find_subparser(self, key):
        return self.SubparserMock(key)

    def find_parser(self, key):
        return self.parsers[key]

class PluginMock(object):
    def __init__(self, name, cls):
        self.name = name
        self.cls = cls

    def iterclasses(self):
        yield self.cls

class PluginManagerMock(object):
    def __init__(self, plugins):
        self.plugins = plugins

    def iterplugins(self):
        for name, cls in self.plugins:
            yield PluginMock(name, cls)

def create_commit(repo, ref, parents, text):
    boid = repo.create_blob(f'{text}\n')
    builder = repo.TreeBuilder()
    builder.insert(f'{text}.txt', boid, pygit2.GIT_FILEMODE_BLOB)
    toid = builder.write()

    author = pygit2.Signature('Alice Author', 'alice@authors.tld')
    committer = author
    return repo.create_commit(
        ref, # the name of the reference to update
        author, committer, f'Say {text}\n\n{text} ',
        toid, # binary string representing the tree object ID
        parents # list of binary strings representing parents of the new commit
    )

def init_remote(remote_path, local_path):
    remote_repo = pygit2.init_repository(str(remote_path), bare=True)

    coid = create_commit(remote_repo, 'refs/heads/master', [], 'Hello')
    coid = create_commit(remote_repo, 'refs/heads/master', [coid], 'Goodbyte')

    local_repo = pygit2.clone_repository(str(remote_path), str(local_path))

    commit = local_repo.revparse_single('HEAD')

    local_repo.branches.create('pushed', commit)
    create_commit(local_repo, 'refs/heads/pushed', [commit.id], 'Pushed')
    # master
    #       \
    #        `---pushed

    local_repo.remotes.add_push('origin', '+refs/heads/*:refs/remotes/origin/*')

    origin = local_repo.remotes['origin']

    commit = local_repo.revparse_single('refs/heads/master')
    merged_remote_coid = create_commit(local_repo, 'refs/heads/master', [commit.id], 'MergedRemote')
    # -------master
    #    \
    #     `---pushed

    commit = local_repo.get(merged_remote_coid)

    local_repo.branches.create('merged_remote', commit)
    # -------master, merged_remote
    #    \
    #     `---pushed

    local_repo.remotes['origin'].push(['refs/heads/master', 'refs/heads/pushed'])
    # -------master, merged_remote, origin/master
    #    \
    #     `---pushed, origin/pushed

    local_repo.branches.create('notpushed', commit)
    local_repo.remotes['origin'].push(['refs/heads/notpushed'])
    create_commit(local_repo, 'refs/heads/notpushed', [commit.id], 'NotPushed')
    # -------master, merged_remote, origin/master
    #    \
    #     `---pushed, origin/pushed, origin/notpushed
    #               \
    #                `---notpushed

    commit = local_repo.revparse_single('refs/heads/master')

    merged_local_coid = create_commit(local_repo,
                                      'refs/heads/master',
                                      [commit.id],
                                      'MergedLocal')
    commit = local_repo.get(merged_local_coid)

    local_repo.branches.create('merged_local', commit)
    # -------merged_remote, origin/master
    #   |                                \
    #   |                                 `---master, merged_local
    #    \
    #     `---pushed, origin/pushed, origin/notpushed
    #               \
    #                `---notpushed

    commit = local_repo.revparse_single('refs/heads/merged_local')

    commit = local_repo.revparse_single('refs/heads/master')

    unmerged_branch = local_repo.branches.create('unmerged', commit)

    unmerged_coid = create_commit(local_repo,
                                  'refs/heads/unmerged',
                                  [commit.id],
                                  'Unmerged')
    # -------merged_remote, origin/master
    #   |                                \
    #   |                                 `---master, merged_local
    #   |                                                         \
    #    \                                                         `---unmerged
    #     `---pushed, origin/pushed, origin/notpushed
    #               \
    #                `---notpushed

    yield remote_repo

def init_clone(url, path):
    repo = pygit2.clone_repository(url, str(path))

    repo.remotes.add_fetch('origin', '+refs/heads/*:refs/remotes/origin/*')
    origin = repo.remotes['origin']
    origin.fetch()

    # -------master, origin/master
    #    \
    #     `---origin/pushed, origin/notpushed

    commit = repo.revparse_single('refs/remotes/origin/master')
    repo.branches.create('merged_remote', commit)
    # -------master, merged_remote, origin/master
    #    \
    #     `---origin/pushed, origin/notpushed

    commit = repo.revparse_single('refs/remotes/origin/pushed')
    repo.branches.create('pushed', commit)
    # -------master, merged_remote, origin/master
    #    \
    #     `---pushed, origin/pushed, origin/notpushed

    repo.branches.create('notpushed', commit)
    create_commit(repo, 'refs/heads/notpushed', [commit.id], 'NotPushed')
    # -------master, merged_remote, origin/master
    #    \
    #     `---pushed, origin/pushed, origin/notpushed
    #               \
    #                `---notpushed

    commit = repo.revparse_single('refs/heads/master')

    merged_local_coid = create_commit(repo,
                                      'refs/heads/master',
                                      [commit.id],
                                      'MergedLocal')
    commit = repo.get(merged_local_coid)

    repo.branches.create('merged_local', commit)
    # -------merged_remote, origin/master
    #   |                                \
    #   |                                 `---master, merged_local
    #    \
    #     `---pushed, origin/pushed, origin/notpushed
    #               \
    #                `---notpushed

    commit = repo.revparse_single('refs/heads/merged_local')

    commit = repo.revparse_single('refs/heads/master')

    unmerged_branch = repo.branches.create('unmerged', commit)

    unmerged_coid = create_commit(repo,
                                  'refs/heads/unmerged',
                                  [commit.id],
                                  'Unmerged')
    # -------merged_remote, origin/master
    #   |                                \
    #   |                                 `---master, merged_local
    #   |                                                         \
    #    \                                                         `---unmerged
    #     `---pushed, origin/pushed, origin/notpushed
    #               \
    #                `---notpushed

    repo.remotes.add_push('origin', '+refs/heads/*:refs/remotes/origin/*')

    yield repo

def init_local_remote(remote_path, clone_path):
    local_clone = pygit2.clone_repository(str(remote_path), str(clone_path), bare=True)

    local_clone.remotes.add_fetch('origin', '+refs/heads/*:refs/remotes/origin/*')

    origin = local_clone.remotes['origin']
    origin.fetch()

    for branch_name in local_clone.branches.remote:
        if branch_name == 'origin/master':
            continue
        branch = local_clone.branches.get(branch_name)
        commit = local_clone.revparse_single(branch.branch_name)
        local_branch_name = branch_name[len(f'{branch.remote_name}/'):]
        local_clone.branches.create(local_branch_name, commit)

    return local_clone

@pytest.fixture(scope="package")
def orig_repository(tmp_path_factory):
    remote_path = tmp_path_factory.mktemp('test_repo.git')
    local_path = tmp_path_factory.mktemp('test_repo_local.git')
    yield from init_remote(remote_path, local_path)

# @pytest.fixture(scope="function")
# def repository_clone(request, remote_repository, tmp_path_factory):
#     with contextlib.ExitStack() as stack:
#         path = tmp_path_factory.mktemp(f'clone_{request.node.name}.git')
#         yield stack.enter_context(init_clone(remote_repository.path, path))

@pytest.fixture(scope="function")
def remote_repository(request, orig_repository, tmp_path_factory):
    path = tmp_path_factory.mktemp(f'local_remote_{request.node.name}.git')
    return init_local_remote(orig_repository.path, path)

@pytest.fixture(scope="function")
def local_repository(request, remote_repository, tmp_path_factory):
    path = tmp_path_factory.mktemp(f'local_remote_clone_{request.node.name}.git')
    yield from init_clone(remote_repository.path, path)

@pytest.fixture(scope="function")
def reset_directory(request, tmp_path_factory):
    path = tmp_path_factory.mktemp(f'reset_dir_{request.node.name}.git')
    os.chdir(path)

@pytest.fixture(scope="function")
def parser_manager_mock(request):
    return ParserManagerMock()

@pytest.fixture(scope="function")
def config_object_class_mock(request):
    return ConfigObjectMock

@pytest.fixture(scope="function")
def plugin_mock(request):
    plugin_name = getattr(request.module, "plugin_name", '')
    plugin_class = getattr(request.module, "plugin_class", '')
    return PluginMock(plugin_name, request.plugin_class)

@pytest.fixture(scope="function")
def git(request, local_repository):
    os.chdir(local_repository.path)
    return git_project.Git()

@pytest.fixture(scope="function")
def gitproject(request, git):
    return git_project.GitProject.get(git)

@pytest.fixture(scope="function")
def project(request, git):
    project_name = 'project'
    return git_project.Project.get(git, project_name)

@pytest.fixture(scope="function")
def parser_manager(request, gitproject, project):
    parser_manager = git_project.ParserManager(gitproject, project)
    parser = parser_manager.find_parser('__main__')

    command_subparser = parser_manager.add_subparser(parser,
                                                     'command',
                                                     dest='command',
                                                     help='commands')
    return parser_manager

@pytest.fixture(scope="function")
def plugin_manager(request):
    return git_project.PluginManager()