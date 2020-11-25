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

def test_init(reset_directory,
              remote_repository,
              local_repository,
              tmp_path_factory):
    path = tmp_path_factory.mktemp('init-workdir')
    os.chdir(path)
    git = git_project.Git()

    assert not git.has_repo()

    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()
    assert git._repo.path == local_repository.path

def test_config(reset_directory, local_repository):
    def check_lines(section,
                    key,
                    value,
                    section_present = True,
                    key_present = True):
        found = False
        with open('config') as conffile:
            found_section = False
            for line in conffile:
                if not found_section:
                    if line.strip() == f'[{section}]':
                        if not section_present:
                            # This shouldn't be here
                            print(f'Section {section} found when should not be')
                            return False
                        found_section = True
                        if not key:
                            return True
                elif key:
                    if line.strip() == f'{key} = {value}':
                        if key_present:
                            return True
                        print(f'2. Key {key} found when should not be')
                        return False

            # Didn't find the section or found the section but not the key.

            if found_section:
                if not section_present:
                    print(f'Section {section} found when should not be')
                    return False
            elif not section_present:
                return True
            elif section_present:
                print(f'Section {section} not found when should be')
                return False

            if not key_present:
                return True

            print(f'Key {key} not found when should be')
            return False

    # Gets to GITDIR
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()
    assert git._repo.path == local_repository.path

    config = git.config

    assert check_lines('test', 'one', '1', section_present=False, key_present=False)

    config.set_item('test', 'one', '1')
    assert check_lines('test', 'one', '1', section_present=True, key_present=True)

    value = config.get_item('test', 'one')
    assert value == '1'

    section = config.get_section('test')

    value = section.get_item('one')
    assert value == '1'

    config.rm_item('test', 'one', '.*')
    assert check_lines('test', 'one', '1', section_present=False, key_present=False)

    # Somehow this doesn't work...
    #config.set_item('test', 'one', '1')
    config.set_item('test', 'two', '2')
    # But this does!  Order matters.  Possibly a bug in pygit2.
    config.set_item('test', 'one', '1')
    assert check_lines('test', 'two', '2', section_present=True, key_present=True)
    assert check_lines('test', 'one', '1', section_present=True, key_present=True)

    config.rm_section('test')
    assert check_lines('test', 'one', '1', section_present=False, key_present=False)

def test_is_bare_repository(reset_directory,
                            remote_repository,
                            local_repository):
    os.chdir(remote_repository.path)

    git = git_project.Git()

    assert git.has_repo()
    assert git.is_bare_repository()

    os.chdir(Path(local_repository.path) / '..')

    git = git_project.Git()

    assert git.has_repo()
    assert not git.is_bare_repository()

def test_worktree(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    # Create a branch for the worktree.
    commit, ref = git._repo.resolve_refish('HEAD')
    branch = git._repo.branches.create('test-wt', commit)

    worktree_checkout_path = Path.cwd() / '..' / '..' / 'test-wt'

    git.add_worktree('test-wt', str(worktree_checkout_path), 'test-wt')

    worktree_path = Path(local_repository.path) / 'worktrees' / 'test-wt'

    assert os.path.exists(worktree_path)

    try:
        git.prune_worktree('test-wt')
        assert False, 'Pruned a worktree when should not have'
    except:
        pass

    shutil.rmtree(worktree_checkout_path)

    git.prune_worktree('test-wt')

    assert not os.path.exists(worktree_path)

def test_get_working_copy_root(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert Path(git.get_working_copy_root()) == (Path(git._repo.path) / '..').resolve()

def test_get_current_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()
    assert git.has_repo()

    assert git.get_current_refname() == 'refs/heads/master'

def test_committish_to_ref(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_to_ref('HEAD').name == 'refs/heads/master'

def test_committish_to_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_to_refname('HEAD') == 'refs/heads/master'

def test_get_committish_oid(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert (git.get_committish_oid('HEAD') ==
            git.get_committish_oid(git.committish_to_refname('HEAD')))

def test_committish_exists(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_exists('refs/heads/master')
    assert git.committish_exists('master')
    assert not git.committish_exists('refs/heads/bogus')
    assert not git.committish_exists('bogus')

def test_is_strict_ancestor(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.is_strict_ancestor('HEAD~', 'HEAD')
    assert not git.is_strict_ancestor('HEAD', 'HEAD~')
    assert not git.is_strict_ancestor('HEAD', 'HEAD')

def test_refname_to_branch_name(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.refname_to_branch_name('refs/heads/master') == 'master'
    assert git.refname_to_branch_name('master') == 'master'

def test_branch_name_to_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.branch_name_to_refname('master') == 'refs/heads/master'
    assert git.branch_name_to_refname('refs/heads/master') == 'refs/heads/master'

def test_get_remote_fetch_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.get_remote_fetch_refname('refs/heads/pushed', 'origin') == 'refs/remotes/origin/pushed'

def test_get_remote_push_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.get_remote_push_refname('refs/heads/pushed', 'origin') == 'refs/remotes/origin/pushed'

def test_get_remote_fetch_refname_oid(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    pushed_commit = git._repo.revparse_single('pushed')
    pushed_oid = pushed_commit.id

    assert git.get_remote_fetch_refname_oid('refs/heads/pushed', 'origin') == pushed_oid

def test_get_remote_push_refname_oid(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    pushed_commit = git._repo.revparse_single('pushed')
    pushed_oid = pushed_commit.id

    assert git.get_remote_push_refname_oid('refs/heads/pushed', 'origin') == pushed_oid

def test_committish_is_pushed(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_is_pushed('pushed', 'origin')
    assert not git.committish_is_pushed('merged_local', 'origin')
    assert not git.committish_is_pushed('notpushed', 'origin')

def test_refname_is_merged(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.refname_is_merged('refs/heads/merged_local', 'refs/heads/master')
    assert not git.refname_is_merged('refs/heads/unmerged', 'refs/heads/master')
    assert git.refname_is_merged('refs/heads/merged_remote',
                                 'refs/remotes/origin/master')
    assert not git.refname_is_merged('refs/heads/notpushed',
                                     'refs/remotes/origin/notpushed')

def test_iterrefnames(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    refnamelist = [refname for refname in git.iterrefnames(['refs/heads/'])]

    assert (refnamelist  ==
            ['refs/heads/master',
             'refs/heads/merged_local',
             'refs/heads/merged_remote',
             'refs/heads/notpushed',
             'refs/heads/pushed',
             'refs/heads/unmerged'])

def test_create_branch(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    git.create_branch('testbranch', 'refs/heads/master')

    assert git.committish_exists('testbranch')
    assert git.refname_is_merged('refs/heads/testbranch', 'refs/heads/master')

    git.create_branch('refs/heads/weirdbranch', 'refs/heads/master')

    assert git.committish_exists('weirdbranch')
    assert git.refname_is_merged('refs/heads/weirdbranch', 'refs/heads/master')

def test_clone(reset_directory, remote_repository, tmp_path_factory):
    path = tmp_path_factory.mktemp('clone-workdir')

    os.chdir(path)

    git = git_project.Git()

    remote_url = 'file://' + remote_repository.path

    clone_path = git.clone(remote_url)
    assert os.path.exists(clone_path)

    os.chdir(clone_path)

    git = git_project.Git()
    assert git.has_repo()
    assert not git.is_bare_repository()

    path = tmp_path_factory.mktemp('bare-clone-workdir')

    os.chdir(path)

    git = git_project.Git()

    clone_path = git.clone(remote_url, bare=True)

    assert os.path.exists(clone_path)

    os.chdir(clone_path)

    git = git_project.Git()
    assert git.has_repo()
    assert git.is_bare_repository()

def test_clone_with_path(reset_directory, remote_repository, tmp_path_factory):
    path = tmp_path_factory.mktemp('clone-workdir')
    os.chdir(path)

    git = git_project.Git()

    remote_url = 'file://' + remote_repository.path

    path = Path.cwd() / 'foo' / 'bar'

    os.makedirs(path)

    path = path / 'test-clone'

    clone_path = git.clone(remote_url, path)

    assert os.path.exists(clone_path)
    assert clone_path == str(path)

def test_checkout(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert (git.get_committish_oid('HEAD') ==
            git.get_committish_oid('master'))

    git.checkout('unmerged')

    assert (git.get_committish_oid('HEAD') ==
            git.get_committish_oid('unmerged'))

    assert not (git.get_committish_oid('master') ==
                git.get_committish_oid('unmerged'))

    git.checkout('master')

    assert (git.get_committish_oid('HEAD') ==
            git.get_committish_oid('master'))

    assert not (git.get_committish_oid('master') ==
                git.get_committish_oid('unmerged'))

def test_update_symbolic_ref(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    git.update_symbolic_ref('HEAD', 'unmerged')

    assert (git.get_committish_oid('HEAD') ==
            git.get_committish_oid('unmerged'))

    assert not (git.get_committish_oid('HEAD') ==
                git.get_committish_oid('master'))

    git.update_symbolic_ref('HEAD', 'master')

    assert not (git.get_committish_oid('HEAD') ==
                git.get_committish_oid('unmerged'))

    assert (git.get_committish_oid('HEAD') ==
            git.get_committish_oid('master'))

def test_delete_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    git.create_branch('todelete', 'HEAD')

    assert git.committish_exists('todelete')
    assert git.committish_exists('refs/heads/todelete')

    git.delete_branch('todelete')

    assert not git.committish_exists('todelete')
    assert not git.committish_exists('refs/heads/todelete')

def test_remote_branch_exists(reset_directory,
                              local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.remote_branch_exists('master', 'origin')
    assert git.remote_branch_exists('pushed', 'origin')
    assert git.remote_branch_exists('notpushed', 'origin')
    assert not git.remote_branch_exists('merged_remote', 'origin')
    assert not git.remote_branch_exists('merged_local', 'origin')
    assert not git.remote_branch_exists('unmerged', 'origin')

def test_delete_remote_refname(reset_directory,
                               local_repository,
                               remote_repository):
    os.chdir(local_repository.path)

    local_git = git_project.Git()

    os.chdir(remote_repository.path)

    remote_git = git_project.Git()

    assert not local_git.committish_exists('todelete')
    assert not local_git.committish_exists('refs/heads/todelete')

    assert not remote_git.committish_exists('todelete')
    assert not remote_git.committish_exists('refs/heads/todelete')

    local_git.create_branch('todelete', 'HEAD')

    assert local_git.committish_exists('todelete')
    assert local_git.committish_exists('refs/heads/todelete')

    local_git._repo.remotes['origin'].push(['refs/heads/todelete'])

    assert remote_git.committish_exists('todelete')
    assert remote_git.committish_exists('refs/heads/todelete')

    assert local_git.committish_exists('refs/remotes/origin/todelete')

    local_git.delete_branch('todelete')

    assert not local_git.committish_exists('todelete')
    assert local_git.committish_exists('refs/remotes/origin/todelete')

    assert remote_git.committish_exists('todelete')
    assert remote_git.committish_exists('refs/heads/todelete')

    local_git.delete_remote_branch('todelete', 'origin')

    assert not local_git.committish_exists('refs/remotes/origin/todelete')

    assert not remote_git.committish_exists('todelete')
    assert not remote_git.committish_exists('refs/heads/todelete')

def test_detach_head(reset_directory,
                     git):
    git.detach_head()
    assert git.head_is_detached()

def test_detach_head_bare(reset_directory,
                          bare_git):
    bare_git.detach_head()
    assert bare_git.head_is_detached()

