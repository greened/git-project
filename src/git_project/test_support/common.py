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

import git_project

import contextlib
import os
from pathlib import Path
import pygit2
import pytest
import pytest_console_scripts
import re

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

def add_blob(repo, parents, text):
    # For now we don't do merge commits.
    assert len(parents) <= 1

    if len(parents) > 0:
        parent_id = parents[0]
        parent_commit = repo.get(parent_id)
        builder = repo.TreeBuilder(parent_commit.tree)
    else:
        builder = repo.TreeBuilder()

    boid = repo.create_blob(f'{text}\n')

    builder.insert(f'{text}.txt', boid, pygit2.GIT_FILEMODE_BLOB)

    toid = builder.write()

    return toid

def create_commit(repo, ref, parents, text):
    # For now we don't do merge commits.
    assert len(parents) <= 1

    toid = add_blob(repo, parents, text)

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
    pushed_commit_oid = create_commit(local_repo,
                                      'refs/heads/pushed',
                                      [commit.id],
                                      'Pushed')
    # master
    #       \
    #        `---pushed

    pushed_commit = local_repo[pushed_commit_oid]
    local_repo.branches.create('notpushed', pushed_commit)
    # master
    #       \
    #        `---pushed, notpushed

    local_repo.remotes.add_push('origin', '+refs/heads/*:refs/remotes/origin/*')

    origin = local_repo.remotes['origin']

    commit = local_repo.revparse_single('refs/heads/master')
    merged_remote_coid = create_commit(local_repo, 'refs/heads/master', [commit.id], 'MergedRemote')
    # -------master
    #    \
    #     `---pushed, notpushed

    commit = local_repo.get(merged_remote_coid)

    local_repo.branches.create('merged_remote', commit)
    local_repo.branches.create('old_master', commit)
    # -------master, merged_remote, old_master
    #    \
    #     `---pushed, notpushed

    commit = local_repo.revparse_single('refs/heads/master')
    merged_remote_coid = create_commit(local_repo, 'refs/heads/master', [commit.id], 'MergedRemote')
    commit = local_repo.get(merged_remote_coid)
    local_repo.branches.create('remote_only', commit)
    commit = local_repo.revparse_single('refs/heads/remote_only')
    merged_remote_coid = create_commit(local_repo, 'refs/heads/remote_only', [commit.id], 'MergedRemote')
    # -------merged_remote, old_master--master--remote_only
    #    \
    #     `---pushed, notpushed

    local_repo.remotes['origin'].push(['refs/heads/master',
                                       'refs/heads/old_master',
                                       'refs/heads/pushed',
                                       'refs/heads/notpushed',
                                       'refs/heads/merged_remote',
                                       'refs/heads/remote_only'])
    # -------merged_remote, old_master, origin/merged_remote, origin/old_master--master, origin/master--origin/remote_only
    #    \
    #     `---pushed, notpushed, origin/notpushed, origin/pushed


    yield remote_repo

def init_clone(url, path):
    repo = pygit2.clone_repository(url, str(path))

    #repo.remotes.add_fetch('origin', '+refs/heads/*:refs/remotes/origin/*')
    origin = repo.remotes['origin']
    origin.fetch()

    # -------origin/old_master, origin/merged_remote--origin/master--origin/remote_only
    #    \
    #     `---origin/notpushed, origin/pushed

    commit = repo.revparse_single('refs/remotes/origin/old_master')
    repo.branches.create('merged_remote', commit)
    # -------merged_remote, origin/old_master, origin/merged_remote--origin/master--origin/remote_only
    #    \
    #     `---origin/notpushed, origin/pushed

    pushed_commit = repo.revparse_single('refs/remotes/origin/pushed')
    repo.branches.create('pushed', pushed_commit)
    # -------merged_remote, origin/old_master, origin/merged_remote--origin/master--origin/remote_only
    #    \
    #     `---origin/notpushed, origin/pushed, pushed

    notpushed_commit = repo.revparse_single('refs/remotes/origin/notpushed')
    repo.branches.create('notpushed', notpushed_commit)

    notpushed_coid = create_commit(repo,
                                   'refs/heads/notpushed',
                                   [pushed_commit.id],
                                   'NotPushed')
    # -------merged_remote, origin/old_master, origin/merged_remote--origin/master--origin/remote_only
    #    \
    #     `---origin/notpushed, origin/pushed, pushed
    #               \
    #                `---notpushed

    repo.checkout('refs/heads/merged_remote')
    master = repo.branches['master']
    master.delete()

    commit = repo.revparse_single('refs/remotes/origin/old_master')
    repo.branches.create('master', commit)
    master = repo.branches['master']
    master.upstream = repo.branches['origin/master']
    # -------merged_remote, origin/old_master, master--origin/master--origin/remote_only
    #    \
    #     `---origin/notpushed, origin/pushed, pushed
    #               \
    #                `---notpushed

    commit = repo.revparse_single('refs/remotes/origin/master')
    repo.branches.create('pushed_indirectly', commit)
    # -------merged_remote, origin/old_master, master--origin/master, pushed_indirectly--origin/remote_only
    #    \
    #     `---origin/notpushed, origin/pushed, pushed
    #               \
    #                `---notpushed

    commit = repo.revparse_single('refs/heads/master')
    merged_local_coid = create_commit(repo,
                                      'refs/heads/master',
                                      [commit.id],
                                      'MergedLocal')
    repo.checkout('refs/heads/master')
    commit = repo.get(merged_local_coid)

    repo.branches.create('merged_local', commit)
    # -------merged_remote, origin/old_master--origin/master, pushed_indirectly--origin/remote_only
    #   |                                \
    #   |                                 `---master, merged_local
    #    \
    #     `---pushed, origin/pushed
    #               \
    #                `---notpushed

    master_commit = repo.revparse_single('refs/heads/master')

    unmerged_branch = repo.branches.create('unmerged', master_commit)

    unmerged_coid = create_commit(repo,
                                  'refs/heads/unmerged',
                                  [master_commit.id],
                                  'Unmerged')
    # -------merged_remote, origin/old_master--origin/master, pushed_indirectly--origin/remote_only
    #   |                                \
    #   |                                 `---master, merged_local--unmerged
    #    \
    #     `---pushed, origin/pushed
    #               \
    #                `---notpushed

    remote_only_commit = repo.revparse_single('refs/remotes/origin/remote_only')

    merged_remote_only_branch = repo.branches.create('merged_remote_only', remote_only_commit)

    # -------merged_remote, origin/old_master--origin/master, pushed_indirectly--origin/remote_only, merged_remote_only
    #   |                                \
    #   |                                 `---master, merged_local--unmerged
    #    \
    #     `---pushed, origin/pushed
    #               \
    #                `---notpushed

    repo.remotes.add_push('origin', '+refs/heads/*:refs/remotes/origin/*')

    yield repo

def init_local_remote(remote_path, clone_path):
    local_clone = pygit2.clone_repository(str(remote_path), str(clone_path), bare=True)

    #local_clone.remotes.add_fetch('origin', '+refs/heads/*:refs/remotes/origin/*')

    origin = local_clone.remotes['origin']
    origin.fetch()

    for branch_name in local_clone.branches.remote:
        if branch_name == 'origin/master' or branch_name == 'origin/HEAD':
            continue
        branch = local_clone.branches.get(branch_name)
        commit = local_clone.revparse_single(branch.branch_name)
        local_branch_name = branch_name[len(f'{branch.remote_name}/'):]
        local_clone.branches.create(local_branch_name, commit)

    return local_clone

@pytest.fixture(scope="function")
def orig_repository(request,
                    tmp_path_factory):
    remote_path = tmp_path_factory.mktemp(f'orig_remote_{request.node.name}.git')
    local_path = tmp_path_factory.mktemp(f'temp_local_{request.node.name}.git')
    yield from init_remote(remote_path, local_path)

# @pytest.fixture(scope="function")
# def repository_clone(request, remote_repository, tmp_path_factory):
#     with contextlib.ExitStack() as stack:
#         path = tmp_path_factory.mktemp(f'clone_{request.node.name}.git')
#         yield stack.enter_context(init_clone(remote_repository.path, path))

@pytest.fixture(scope="function")
def remote_repository(request,
                      reset_directory,
                      orig_repository,
                      tmp_path_factory):
    path = tmp_path_factory.mktemp(f'local_remote_{request.node.name}.git')
    return init_local_remote(orig_repository.path, path)

@pytest.fixture(scope="function")
def reset_directory(request, tmp_path_factory):
    path = tmp_path_factory.mktemp(f'reset_dir_{request.node.name}.git')
    os.chdir(path)

@pytest.fixture(scope="function")
def local_repository(request,
                     reset_directory,
                     remote_repository,
                     tmp_path_factory):
    path = tmp_path_factory.mktemp(f'local_remote_clone_{request.node.name}.git')
    yield from init_clone(remote_repository.path, path)

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
def bare_git(request, remote_repository):
    os.chdir(remote_repository.path)
    return git_project.Git()

@pytest.fixture(scope="function")
def gitproject(request, git):
    return git_project.GitProject.get(git)

@pytest.fixture(scope="function")
def project(request, git):
    project_name = 'project'
    project = git_project.Project.get(git, project_name)
    project.add_branch('remote_only')
    return project

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

class GitProjectRunner(object):
    def __init__(self, runner, directory):
        self.command = 'git-project'
        self.runner = runner
        self.directory = directory
        self.expect_fail = False

    def chdir(self, path):
        self.directory = str(path)

    def run(self, expected_stdout_regexp, expected_stderr_regexp, *args, **kwargs):
        result = self.runner.run(self.command, *args, cwd=self.directory, **kwargs)

        if self.expect_fail:
            assert not result.success
        else:
            assert result.success

        stdout_re = re.compile(expected_stdout_regexp, re.M)
        stderr_re = re.compile(expected_stderr_regexp, re.M)

        assert stdout_re.search(result.stdout)
        assert stderr_re.search(result.stderr)

@pytest.fixture(scope="function")
def git_project_runner(reset_directory, script_runner):
    result = GitProjectRunner(script_runner, Path.cwd())
    return result

def check_config_file(section,
                      key,
                      values,
                      section_present = True,
                      key_present = True):
    found = False
    parts = section.split('.', 1)
    prefix = parts[0]
    suffix = parts[1] if len(parts) == 2 else None

    found_values = set()
    lines = []
    with open('config') as conffile:
        found_section = False
        in_section = False
        for line in conffile:
            lines.append(line)
            match = re.match(r'^\[([^\s]*)( "([^"]*)")?\]$',
                             line.strip())
            if match:
                matched_section = match.group(1)
                matched_subsection = match.group(3)  # Could be None
                if matched_section == prefix and matched_subsection == suffix:
                    if not key and section_present:
                        # We only care that the section is present
                        return
                    found_section = True
                    in_section = True
                else:
                    in_section = False
            elif key and in_section:
                match = re.match(f'^\\s*{key} = (.*)$', line.strip())
                if match:
                    matched_value = match.group(1)
                    if matched_value in found_values:
                        for line in lines:
                            print(line.rstrip())
                        print(f'Duplicate values {key} = {matched_value}')
                    assert not matched_value in found_values
                    found_values.add(matched_value)

        if found_section:
            assert section_present
        else:
            assert not section_present
            # Don't check values.
            return

        if not found_values:
            assert not key_present
            return

        if values:
            if not found_values == values:
                for line in lines:
                    print(line.rstrip())
                print(f'Expected: {section} {key} = {values}')
                print(f'Found: {section} {key} = {found_values}')
            assert found_values == values
