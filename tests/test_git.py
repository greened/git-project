#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2020-present David A. Greene <dag@obbligato.org>

# SPDX-License-Identifier: AGPL-3.0-or-later

# Copyright 2020 David A. Greene

# This file is part of git-project

# git-project is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License along
# with git-project. If not, see <https://www.gnu.org/licenses/>.

import itertools
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pygit2
import pytest

import git_project
from git_project.test_support.common import create_commit


def test_git_init(
    reset_directory, remote_repository, local_repository, tmp_path_factory
):
    path = tmp_path_factory.mktemp("init-workdir")
    os.chdir(path)
    git = git_project.Git()

    assert not git.has_repo()

    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()
    assert git._repo.path == local_repository.path


@pytest.mark.parametrize(
    "accessor", ["_repo", "config", "is_bare_repository", "get_main_branch"]
)
def test_git_outside_repository_reports_it(
    reset_directory, tmp_path_factory, accessor
):
    path = tmp_path_factory.mktemp("no-repo-workdir")
    os.chdir(path)
    git = git_project.Git()

    assert not git.has_repo()

    with pytest.raises(git_project.GitProjectError) as exc:
        # A property raises on the read, a method on the call.
        result = getattr(git, accessor)
        if callable(result):
            result()

    assert str(path) in str(exc.value)


def test_git_committish_exists_outside_repository_reports_it(
    reset_directory, tmp_path_factory
):
    path = tmp_path_factory.mktemp("committish-no-repo-workdir")
    os.chdir(path)
    git = git_project.Git()

    # committish_exists takes an argument, so the parametrized spec above
    # cannot drive it.  Its bare except answers False for every fault it
    # covers, so the repository read has to stay outside.  False here would
    # say the committish is absent rather than that there is nothing to look
    # in.
    with pytest.raises(git_project.GitProjectError) as exc:
        git.committish_exists("HEAD")

    assert str(path) in str(exc.value)


def test_git_reinit_searches_the_path_it_reports(
    reset_directory, local_repository
):
    os.chdir(local_repository.path)
    git = git_project.Git()

    # reinit records the resolved path, so it has to search that same path.
    # Searching the caller's path instead detaches from a repository that is
    # right here, then names the resolved path as having none.
    git.reinit("")

    assert git.has_repo()


def test_git_reinit_outside_repository_detaches(
    reset_directory, local_repository, tmp_path_factory
):
    os.chdir(local_repository.path)
    git = git_project.Git()

    assert git.has_repo()

    # Re-pointing an attached Git at a path with no repository detaches it.
    # Answering has_repo True here would report the previous repository.
    path = tmp_path_factory.mktemp("reinit-no-repo-workdir")
    git.reinit(path)

    assert not git.has_repo()

    with pytest.raises(git_project.GitProjectError) as exc:
        git.is_bare_repository()

    assert str(path) in str(exc.value)

    # The config reports no repository too, rather than handing back the one
    # belonging to the repository we just left.
    with pytest.raises(git_project.GitProjectError) as exc:
        _ = git.config

    assert str(path) in str(exc.value)

    # Re-pointing back at a repository reattaches.  Both fields have to come
    # back, so read the config as well: it raises when either one is empty.
    git.reinit(local_repository.path)

    assert git.has_repo()
    assert not git.is_bare_repository()

    _ = git.config


def test_git_config(reset_directory, local_repository):
    def check_lines(
        section, key, value, section_present=True, key_present=True
    ):
        with open("config") as conffile:
            found_section = False
            for line in conffile:
                if not found_section:
                    if line.strip() == f"[{section}]":
                        if not section_present:
                            # This shouldn't be here
                            print(
                                f"Section {section} found when should not be"
                            )
                            return False
                        found_section = True
                        if not key:
                            return True
                elif line.strip().startswith("["):
                    break
                elif key:
                    if line.strip() == f"{key} = {value}":
                        if key_present:
                            return True
                        print(f"2. Key {key} found when should not be")
                        return False

            # Didn't find the section or found the section but not the key.

            if found_section:
                if not section_present:
                    print(f"Section {section} found when should not be")
                    return False
            elif not section_present:
                return True
            elif section_present:
                print(f"Section {section} not found when should be")
                return False

            if not key_present:
                return True

            print(f"Key {key} not found when should be")
            return False

    # Gets to GITDIR
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()
    assert git._repo.path == local_repository.path

    config = git.config

    assert check_lines(
        "test", "one", "1", section_present=False, key_present=False
    )

    config.set_item("test", "one", "1")
    assert check_lines(
        "test", "one", "1", section_present=True, key_present=True
    )

    value = config.get_item("test", "one")
    assert value == "1"

    section = config.get_section("test")

    value = section.get_item("one")
    assert value == "1"

    config.rm_item("test", "one", ".*")
    assert check_lines(
        "test", "one", "1", section_present=False, key_present=False
    )

    # Somehow this doesn't work...
    # config.set_item('test', 'one', '1')
    config.set_item("test", "two", "2")
    # But this does!  Order matters.  Possibly a bug in pygit2.
    config.set_item("test", "one", "1")
    assert check_lines(
        "test", "two", "2", section_present=True, key_present=True
    )
    assert check_lines(
        "test", "one", "1", section_present=True, key_present=True
    )

    config.rm_section("test")
    assert check_lines(
        "test", "one", "1", section_present=False, key_present=False
    )

    config.set_item("testrm", "one", "1")
    values = list(config.iter_multival("testrm", "one"))
    assert values == ["1"]

    config.rm_item("testrm", "one", ".*")
    assert check_lines(
        "testrm", "one", "1", section_present=False, key_present=False
    )

    config.set_item("testrm2", "one", "1")
    values = list(config.iter_multival("testrm2", "one"))
    assert values == ["1"]

    # Make sure we still delete things if we're not in the git repository.
    prev_dir = Path.cwd()
    os.chdir(Path.cwd().parent.parent)
    new_dir = Path.cwd()
    config.rm_item("testrm2", "one", ".*")
    assert Path.cwd() == new_dir
    os.chdir(prev_dir)
    assert check_lines(
        "testrm2", "one", "1", section_present=False, key_present=False
    )

    config.set_item("testrm3", "one", "1")
    config.add_item("testrm3", "one", "2")
    values = list(config.iter_multival("testrm3", "one"))
    assert set(values) == {"1", "2"}

    config.rm_items("testrm3", "one")
    assert check_lines(
        "testrm3", "one", "1", section_present=False, key_present=False
    )
    assert check_lines(
        "testrm3", "one", "2", section_present=False, key_present=False
    )

    config.set_item("testrm4", "one", "1")
    config.add_item("testrm4", "one", "2")
    values = list(config.iter_multival("testrm4", "one"))
    assert set(values) == {"1", "2"}

    # Make sure we still delete things if we're not in the git repository.
    prev_dir = Path.cwd()
    os.chdir(Path.cwd().parent.parent)
    new_dir = Path.cwd()
    config.rm_items("testrm4", "one")
    assert Path.cwd() == new_dir
    os.chdir(prev_dir)
    assert check_lines(
        "testrm4", "one", "1", section_present=False, key_present=False
    )
    assert check_lines(
        "testrm4", "one", "2", section_present=False, key_present=False
    )


def test_git_config_rm_item_with_space(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()
    config = git.config

    config.set_item("testspace", "cmd", "make")
    config.add_item("testspace", "cmd", "cd build && make")

    config.rm_item("testspace", "cmd", "cd build && make")

    assert list(config.iter_multival("testspace", "cmd")) == ["make"]
    assert list(
        git_project.Git().config.iter_multival("testspace", "cmd")
    ) == ["make"]


def test_git_is_bare_repository(
    reset_directory, remote_repository, local_repository
):
    os.chdir(remote_repository.path)

    git = git_project.Git()

    assert git.has_repo()
    assert git.is_bare_repository()

    os.chdir(Path(local_repository.path) / "..")

    git = git_project.Git()

    assert git.has_repo()
    assert not git.is_bare_repository()


def test_git_worktree(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    # Create a branch for the worktree.
    commit, _ref = git._repo.resolve_refish("HEAD")
    git._repo.branches.create("test-wt", commit)

    worktree_checkout_path = Path.cwd() / ".." / ".." / "test-wt"

    git.add_worktree("test-wt", str(worktree_checkout_path), "test-wt")

    worktree_path = Path(local_repository.path) / "worktrees" / "test-wt"

    assert os.path.exists(worktree_path)

    with pytest.raises(
        git_project.GitProjectError,
        match="Will not prune existing worktree test-wt",
    ):
        git.prune_worktree("test-wt")

    shutil.rmtree(worktree_checkout_path)

    git.prune_worktree("test-wt")

    assert not os.path.exists(worktree_path)


def test_git_add_worktree_tag_shadows_branch(
    reset_directory, local_repository
):
    os.chdir(local_repository.path)

    git = git_project.Git()

    commit, _ref = git._repo.resolve_refish("HEAD")
    git._repo.branches.create("test-wt", commit)
    git._repo.references.create("refs/tags/test-wt", commit.id)

    worktree_checkout_path = Path.cwd() / ".." / ".." / "test-wt"

    git.add_worktree("test-wt", str(worktree_checkout_path), "test-wt")

    worktree_repo = pygit2.Repository(str(worktree_checkout_path))
    assert worktree_repo.head.name == "refs/heads/test-wt"

    shutil.rmtree(worktree_checkout_path)
    git.prune_worktree("test-wt")


def test_git_get_working_copy_root(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert (
        Path(git.get_working_copy_root())
        == (Path(git._repo.path) / "..").resolve()
    )


def test_git_get_current_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()
    assert git.has_repo()

    assert git.get_current_refname() == "refs/heads/master"


def test_git_committish_to_ref(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_to_ref("HEAD").name == "refs/heads/master"


def test_git_committish_to_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_to_refname("HEAD") == "refs/heads/master"


def test_git_branch_or_committish_ref_tag_shadows_branch(
    reset_directory, local_repository
):
    os.chdir(local_repository.path)

    master = local_repository.revparse_single("refs/heads/master")
    local_repository.references.create("refs/tags/unmerged", master.id)
    local_repository.references.create("refs/tags/only-a-tag", master.id)

    git = git_project.Git()

    assert (
        git.branch_or_committish_ref("unmerged").name == "refs/heads/unmerged"
    )
    assert (
        git.branch_or_committish_ref("only-a-tag").name
        == "refs/tags/only-a-tag"
    )
    assert git.branch_or_committish_ref("HEAD").name == "refs/heads/master"
    assert git.branch_or_committish_ref("master~1") is None
    assert git.branch_or_committish_ref(str(master.id)) is None


def test_git_get_committish_oid(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.get_committish_oid("HEAD") == git.get_committish_oid(
        git.committish_to_refname("HEAD")
    )


def test_git_committish_exists(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_exists("refs/heads/master")
    assert git.committish_exists("master")
    assert not git.committish_exists("refs/heads/bogus")
    assert not git.committish_exists("bogus")


def test_git_is_strict_ancestor(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.is_strict_ancestor("HEAD~", "HEAD")
    assert not git.is_strict_ancestor("HEAD", "HEAD~")
    assert not git.is_strict_ancestor("HEAD", "HEAD")


def test_git_refname_to_branch_name(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.refname_to_branch_name("refs/heads/master") == "master"
    assert git.refname_to_branch_name("master") == "master"


def test_git_refname_to_branch_name_remote(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert (
        git.refname_to_branch_name("refs/remotes/origin/master")
        == "origin/master"
    )
    assert git.refname_to_branch_name("origin/master") == "origin/master"


def test_git_branch_name_to_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.branch_name_to_refname("master") == "refs/heads/master"
    assert (
        git.branch_name_to_refname("refs/heads/master") == "refs/heads/master"
    )


def test_git_branch_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.branch_refname("master") == "refs/heads/master"
    assert git.branch_refname("origin/master") == "refs/remotes/origin/master"


def test_git_get_remote_fetch_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert (
        git.get_remote_fetch_refname("refs/heads/pushed", "origin")
        == "refs/remotes/origin/pushed"
    )


def test_git_get_remote_push_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert (
        git.get_remote_push_refname("refs/heads/pushed", "origin")
        == "refs/remotes/origin/pushed"
    )


def test_git_get_remote_fetch_refname_oid(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    pushed_commit = git._repo.revparse_single("pushed")
    pushed_oid = pushed_commit.id

    assert (
        git.get_remote_fetch_refname_oid("refs/heads/pushed", "origin")
        == pushed_oid
    )


def test_git_get_remote_push_refname_oid(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    pushed_commit = git._repo.revparse_single("pushed")
    pushed_oid = pushed_commit.id

    assert (
        git.get_remote_push_refname_oid("refs/heads/pushed", "origin")
        == pushed_oid
    )


def test_git_committish_is_pushed(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.committish_is_pushed("pushed", "origin")
    assert not git.committish_is_pushed("merged_local", "origin")
    assert not git.committish_is_pushed("notpushed", "origin")


def test_git_committish_is_pushed_tag_shadows_branch(
    reset_directory, local_repository
):
    os.chdir(local_repository.path)

    pushed = local_repository.revparse_single("refs/heads/pushed")
    notpushed = local_repository.revparse_single("refs/heads/notpushed")
    local_repository.references.create("refs/tags/pushed", notpushed.id)
    local_repository.references.create("refs/tags/notpushed", pushed.id)

    git = git_project.Git()

    assert git.committish_is_pushed("pushed", "origin")
    assert not git.committish_is_pushed("notpushed", "origin")


def test_git_refname_is_merged(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    assert git.refname_is_merged(
        "refs/heads/merged_local", "refs/heads/master"
    )
    assert not git.refname_is_merged(
        "refs/heads/unmerged", "refs/heads/master"
    )
    assert git.refname_is_merged(
        "refs/heads/merged_remote", "refs/remotes/origin/master"
    )
    assert not git.refname_is_merged(
        "refs/heads/notpushed", "refs/remotes/origin/notpushed"
    )
    assert git.refname_is_merged("merged_local", "master")
    assert not git.refname_is_merged("merged_local", "nonexistent")


def test_git_refname_is_merged_tag_shadows_branch(
    reset_directory, local_repository
):
    os.chdir(local_repository.path)

    pushed = local_repository.revparse_single("refs/heads/pushed")
    local_repository.references.create("refs/tags/master", pushed.id)

    git = git_project.Git()

    assert git.refname_is_merged("refs/heads/merged_local", "master")
    assert not git.refname_is_merged("refs/heads/pushed", "master")


def test_git_iterrefnames(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    refnamelist = list(git.iterrefnames(["refs/heads/"]))

    assert refnamelist == [
        "refs/heads/master",
        "refs/heads/merged_local",
        "refs/heads/merged_remote",
        "refs/heads/notpushed",
        "refs/heads/pushed",
        "refs/heads/pushed_indirectly",
        "refs/heads/pushed_remote_only",
        "refs/heads/unmerged",
    ]


def test_git_iterrefnames_str(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    refnamelist = list(git.iterrefnames("refs/heads/"))

    assert refnamelist == [
        "refs/heads/master",
        "refs/heads/merged_local",
        "refs/heads/merged_remote",
        "refs/heads/notpushed",
        "refs/heads/pushed",
        "refs/heads/pushed_indirectly",
        "refs/heads/pushed_remote_only",
        "refs/heads/unmerged",
    ]


def test_git_create_branch(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    git.create_branch("testbranch", "refs/heads/master")

    assert git.committish_exists("testbranch")
    assert git.refname_is_merged("refs/heads/testbranch", "refs/heads/master")

    git.create_branch("refs/heads/weirdbranch", "refs/heads/master")

    assert git.committish_exists("weirdbranch")
    assert git.refname_is_merged("refs/heads/weirdbranch", "refs/heads/master")


def test_git_clone(reset_directory, remote_repository, tmp_path_factory):
    path = tmp_path_factory.mktemp("clone-workdir")

    os.chdir(path)

    git = git_project.Git()

    remote_url = "file://" + remote_repository.path

    clone_path = git.clone(remote_url, "id_rsa")
    assert os.path.exists(clone_path)

    os.chdir(clone_path)

    git = git_project.Git()
    assert git.has_repo()
    assert not git.is_bare_repository()

    path = tmp_path_factory.mktemp("bare-clone-workdir")

    os.chdir(path)

    git = git_project.Git()

    clone_path = git.clone(remote_url, "id_rsa", bare=True)

    assert os.path.exists(clone_path)

    os.chdir(clone_path)

    git = git_project.Git()
    assert git.has_repo()
    assert git.is_bare_repository()


def test_git_clone_with_path(
    reset_directory, remote_repository, tmp_path_factory
):
    path = tmp_path_factory.mktemp("clone-workdir")
    os.chdir(path)

    git = git_project.Git()

    remote_url = "file://" + remote_repository.path

    path = Path.cwd() / "foo" / "bar"

    os.makedirs(path)

    path = path / "test-clone"

    clone_path = git.clone(remote_url, "id_rsa", path)

    assert os.path.exists(clone_path)
    assert clone_path == str(path)


def test_git_clone_without_ssh_id(
    reset_directory, remote_repository, tmp_path_factory
):
    path = tmp_path_factory.mktemp("no-ssh-id-clone-workdir")

    os.chdir(path)

    git = git_project.Git()

    remote_url = "file://" + remote_repository.path

    clone_path = git.clone(remote_url)

    assert os.path.exists(clone_path)

    os.chdir(clone_path)

    git = git_project.Git()
    assert git.has_repo()
    assert not git.is_bare_repository()


# A stand-in for ssh that runs the remote command locally.
# GIT_SSH_VARIANT=simple makes git pass only the host and the command.
FAKE_SSH = 'shift\nexec sh -c "$1"\n'


def use_fake_ssh(directory, monkeypatch, body=FAKE_SSH):
    ssh = Path(directory) / "fake-ssh"
    ssh.write_text("#!/bin/sh\n" + body)
    ssh.chmod(0o755)
    monkeypatch.setenv("GIT_SSH_COMMAND", str(ssh))
    monkeypatch.setenv("GIT_SSH_VARIANT", "simple")


def make_source(path):
    repo = pygit2.init_repository(str(path), bare=True)
    coid = create_commit(repo, "refs/heads/master", [], "Hello")
    create_commit(repo, "refs/heads/feature", [coid], "Feature")
    repo.set_head("refs/heads/master")
    return repo


def clone_layout(path, branch="master"):
    repo = pygit2.Repository(path)
    config = repo.config
    keys = [
        "remote.origin.fetch",
        f"branch.{branch}.remote",
        f"branch.{branch}.merge",
    ]
    return {
        "config": {
            key: config[key] if key in config else None for key in keys
        },
        "refs": {
            ref
            for ref in repo.references
            if ref.startswith(("refs/heads/", "refs/remotes/"))
        },
        "head": repo.references["HEAD"].target,
        "origin_head": repo.references["refs/remotes/origin/HEAD"].target,
    }


def assert_exits(pid):
    for _ in range(50):
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
        except FileNotFoundError:
            return
        # A zombie has exited and waits only for its parent to reap it.
        if stat.rpartition(")")[2].split()[0] == "Z":
            return
        time.sleep(0.1)
    pytest.fail("ssh outlived git")


@pytest.mark.parametrize(
    "url, expected",
    [
        ("ssh://example.invalid/x.git", True),
        ("git+ssh://example.invalid/x.git", True),
        ("ssh+git://example.invalid/x.git", True),
        ("SSH://example.invalid/x.git", True),
        ("git@github.com:greened/x.git", True),
        ("example.invalid:/x.git", True),
        ("[::1]:x.git", True),
        ("https://example.invalid/x.git", False),
        ("file:///tmp/x.git", False),
        ("/tmp/x.git", False),
        ("x.git", False),
        ("./a:b", False),
        ("/tmp/a:b", False),
        ("ext::ssh example.invalid %S x.git", False),
        ("helper::ssh://example.invalid/x.git", False),
    ],
)
def test_git_is_ssh_url(url, expected):
    assert git_project.Git._is_ssh_url(url, "cannot use the url") == expected


def test_git_clone_malformed_url(reset_directory, tmp_path_factory):
    os.chdir(tmp_path_factory.mktemp("ssh-clone-workdir"))

    with pytest.raises(
        git_project.GitProjectError, match=r"^cannot clone: cannot parse"
    ):
        git_project.Git().clone("ssh://[::1")


def test_git_fetch_remote_malformed_url(reset_directory, local_repository):
    os.chdir(local_repository.path)
    git = git_project.Git()
    git.config.set_item("remote.origin", "url", "ssh://[::1")

    with pytest.raises(
        git_project.GitProjectError,
        match=r"^cannot fetch from remote origin: cannot parse",
    ):
        git.fetch_remote("origin")


@pytest.mark.parametrize("bare", [False, True])
@pytest.mark.parametrize(
    "form",
    ["ssh://example.invalid{}", "example.invalid:{}"],
    ids=["ssh-scheme", "scp"],
)
def test_git_clone_ssh_matches_libgit2(
    reset_directory, tmp_path_factory, monkeypatch, form, bare
):
    source = tmp_path_factory.mktemp("ssh-source")
    make_source(source)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    use_fake_ssh(workdir, monkeypatch)

    libgit2_path = git_project.Git().clone(
        f"file://{source}", path=str(workdir / "libgit2"), bare=bare
    )
    url = form.format(source)
    git = git_project.Git()
    # libgit2 cannot resolve example.invalid, so success means the CLI ran.
    clone_path = git.clone(url, bare=bare)

    assert clone_path == str(workdir / source.name)
    assert git.is_bare_repository() == bare
    assert git.get_remote_url("origin") == url
    layout = clone_layout(clone_path)
    assert layout == clone_layout(libgit2_path)
    assert {
        "refs/remotes/origin/master",
        "refs/remotes/origin/feature",
    } <= layout["refs"]
    if not bare:
        assert (Path(clone_path) / "Hello.txt").exists()
        assert git.workarea_is_clean()


@pytest.fixture
def libgit2_config(tmp_path_factory):
    # GIT_CONFIG_GLOBAL reaches only the CLI, so without this libgit2 would
    # read the user's init.defaultBranch.
    home = tmp_path_factory.mktemp("libgit2-config")
    levels = [
        pygit2.enums.ConfigLevel.GLOBAL,
        pygit2.enums.ConfigLevel.XDG,
        pygit2.enums.ConfigLevel.SYSTEM,
    ]
    saved = {level: pygit2.settings.search_path[level] for level in levels}
    for level in levels:
        pygit2.settings.search_path[level] = str(home)
    yield home / ".gitconfig"
    for level, path in saved.items():
        pygit2.settings.search_path[level] = path


@pytest.mark.parametrize("initial", [None, "main"])
@pytest.mark.parametrize("branch", ["master", "feature"])
def test_git_clone_ssh_detached_remote_head(
    reset_directory,
    tmp_path_factory,
    monkeypatch,
    libgit2_config,
    branch,
    initial,
):
    source = tmp_path_factory.mktemp("ssh-source")
    source_repo = make_source(source)
    # Another branch at the same commit, which sorts first.
    oid = source_repo.references[f"refs/heads/{branch}"].target
    source_repo.references.create("refs/heads/aaa", oid)
    if initial:
        # It sorts after aaa, so only its being the initial branch picks it.
        source_repo.references.create(f"refs/heads/{initial}", oid)
        libgit2_config.write_text(f"[init]\n\tdefaultBranch = {initial}\n")
    # A detached HEAD sends no symref, so the clone guesses the branch.
    source_repo.set_head(oid)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    use_fake_ssh(workdir, monkeypatch)

    libgit2_path = git_project.Git().clone(
        f"file://{source}", path=str(workdir / "libgit2")
    )
    clone_path = git_project.Git().clone(f"ssh://example.invalid{source}")

    expected = initial or ("master" if branch == "master" else "aaa")
    layout = clone_layout(clone_path, expected)
    assert layout == clone_layout(libgit2_path, expected)
    assert layout["head"] == f"refs/heads/{expected}"
    assert pygit2.Repository(clone_path).head.target == oid


def test_git_clone_ssh_head_on_no_branch(
    reset_directory, tmp_path_factory, monkeypatch
):
    source = tmp_path_factory.mktemp("ssh-source")
    source_repo = make_source(source)
    parent = source_repo.references["refs/heads/feature"].target
    loose = create_commit(source_repo, None, [parent], "Loose")
    source_repo.set_head(loose)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    use_fake_ssh(workdir, monkeypatch)

    clone_path = git_project.Git().clone(f"ssh://example.invalid{source}")

    repo = pygit2.Repository(clone_path)
    assert repo.head_is_detached
    assert repo.head.target == loose
    assert (Path(clone_path) / "Loose.txt").exists()
    assert set(repo.branches.local) == set()


@pytest.mark.parametrize("fails", [False, True])
def test_git_clone_ssh_missing_parents(
    reset_directory, tmp_path_factory, monkeypatch, fails
):
    source = tmp_path_factory.mktemp("ssh-source")
    make_source(source)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    (workdir / "a").mkdir()
    body = FAKE_SSH
    if fails:
        marker = workdir / "connected"
        body = (
            f"if [ -e {marker} ]; then echo denied >&2; exit 255; fi\n"
            f"touch {marker}\n{FAKE_SSH}"
        )
    use_fake_ssh(workdir, monkeypatch, body)
    target = workdir / "a" / "b" / "c" / "x.git"
    url = f"ssh://example.invalid{source}"

    if not fails:
        clone_path = git_project.Git().clone(url, path=str(target), bare=True)
        assert clone_path == str(target)
        assert "refs/heads/master" in pygit2.Repository(clone_path).references
        return

    with pytest.raises(git_project.GitProjectError, match="denied"):
        git_project.Git().clone(url, path=str(target), bare=True)

    # The clone made b and c, and a was there before.
    assert list((workdir / "a").iterdir()) == []


def test_git_clone_ssh_ignores_caller_repository(
    reset_directory, tmp_path_factory, monkeypatch
):
    source = tmp_path_factory.mktemp("ssh-source")
    make_source(source)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    caller = pygit2.init_repository(str(workdir))
    # If git read this config, the rewrite would send it to a source that
    # does not exist.
    caller.config["url.ssh://example.invalid/nowhere.insteadOf"] = (
        "ssh://example.invalid"
    )
    os.chdir(workdir)
    monkeypatch.setenv("GIT_DIR", caller.path)
    monkeypatch.setenv("GIT_WORK_TREE", str(workdir))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(workdir / "objects"))
    use_fake_ssh(workdir, monkeypatch)

    clone_path = git_project.Git().clone(
        f"ssh://example.invalid{source}", path=str(workdir / "clone")
    )

    assert (Path(clone_path) / "Hello.txt").exists()
    assert pygit2.Repository(clone_path).head.shorthand == "master"


def test_git_clone_ssh_empty_remote(
    reset_directory, tmp_path_factory, monkeypatch
):
    source = tmp_path_factory.mktemp("ssh-source")
    pygit2.init_repository(str(source), bare=True)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    use_fake_ssh(workdir, monkeypatch)

    git = git_project.Git()
    clone_path = git.clone(f"ssh://example.invalid{source}", bare=True)

    repo = pygit2.Repository(clone_path)
    assert repo.head_is_unborn
    assert repo.remotes["origin"].url == f"ssh://example.invalid{source}"


@pytest.mark.parametrize("operation", ["clone", "fetch"])
def test_git_ssh_transfer_failure(
    reset_directory, local_repository, tmp_path_factory, monkeypatch, operation
):
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    use_fake_ssh(
        workdir,
        monkeypatch,
        "echo 'Permission denied (publickey).' >&2\nexit 255\n",
    )
    url = "example.invalid:/srv/x.git"
    if operation == "clone":
        os.chdir(workdir)
        git = git_project.Git()
        prefix = f"cannot clone {url}"
    else:
        os.chdir(local_repository.path)
        git = git_project.Git()
        git.config.set_item("remote.origin", "url", url)
        prefix = "cannot fetch from remote origin"

    with pytest.raises(git_project.GitProjectError) as info:
        if operation == "clone":
            git.clone(url)
        else:
            git.fetch_remote("origin")

    message = str(info.value)
    assert message.startswith(f"{prefix}: Permission denied")
    assert "\n" not in message
    assert not (workdir / "x.git").exists()


@pytest.mark.parametrize(
    "owner, name",
    [
        (pygit2, "init_repository"),
        (pygit2.remotes.RemoteCollection, "create"),
        (pygit2.branches.Branches, "create"),
        (pygit2.Repository, "checkout_head"),
    ],
    ids=["init", "remote", "branch", "checkout"],
)
def test_git_clone_ssh_pygit2_failure(
    reset_directory, tmp_path_factory, monkeypatch, owner, name
):
    source = tmp_path_factory.mktemp("ssh-source")
    make_source(source)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    use_fake_ssh(workdir, monkeypatch)

    def fail(*args, **kwargs):
        raise pygit2.GitError("broken by the test")

    monkeypatch.setattr(owner, name, fail)

    with pytest.raises(
        git_project.GitProjectError,
        match=r"^cannot clone ssh://.*: broken by the test$",
    ):
        git_project.Git().clone(f"ssh://example.invalid{source}")

    assert not (workdir / source.name).exists()


@pytest.mark.parametrize("existed", [False, True])
def test_git_clone_ssh_fetch_failure_removes_clone(
    reset_directory, tmp_path_factory, monkeypatch, existed
):
    source = tmp_path_factory.mktemp("ssh-source")
    make_source(source)
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    target = workdir / source.name
    if existed:
        target.mkdir()
    # The ls-remote succeeds and the fetch after it fails.
    marker = workdir / "connected"
    use_fake_ssh(
        workdir,
        monkeypatch,
        f"if [ -e {marker} ]; then echo denied >&2; exit 255; fi\n"
        f"touch {marker}\n{FAKE_SSH}",
    )

    git = git_project.Git()
    with pytest.raises(git_project.GitProjectError, match="denied"):
        git.clone(f"ssh://example.invalid{source}")

    if existed:
        assert list(target.iterdir()) == []
    else:
        assert not target.exists()


def test_git_clone_ssh_timeout(reset_directory, tmp_path_factory, monkeypatch):
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    pidfile = workdir / "ssh.pid"
    use_fake_ssh(workdir, monkeypatch, f"echo $$ > {pidfile}\nexec sleep 30\n")
    monkeypatch.setattr(git_project.Git, "REMOTE_TIMEOUT", 3)

    git = git_project.Git()
    with pytest.raises(git_project.GitProjectError, match="timed out after 3"):
        git.clone("ssh://example.invalid/srv/x.git")

    assert_exits(int(pidfile.read_text()))
    assert not (workdir / "x.git").exists()


def test_git_clone_ssh_interrupt(
    reset_directory, tmp_path_factory, monkeypatch
):
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    pidfile = workdir / "ssh.pid"
    use_fake_ssh(workdir, monkeypatch, f"echo $$ > {pidfile}\nexec sleep 30\n")

    class Interrupted(subprocess.Popen):
        # Ctrl-C reaches only Python, because git runs in a new session.
        def communicate(self, timeout=None):
            for _ in range(50):
                if pidfile.exists() and pidfile.read_text().strip():
                    break
                time.sleep(0.1)
            raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "Popen", Interrupted)

    git = git_project.Git()
    with pytest.raises(KeyboardInterrupt):
        git.clone("ssh://example.invalid/srv/x.git")

    assert_exits(int(pidfile.read_text()))
    assert not (workdir / "x.git").exists()


def record_git(monkeypatch):
    """Stand in for git, and return the list each command is added to. Only
    ls-remote succeeds.

    """
    commands = []

    class Recorder:
        def __init__(self, command, **kwargs):
            commands.append(command)
            self.returncode = 0 if "ls-remote" in command else 128

        def communicate(self, timeout=None):
            return "", "fatal: stopped by the test\n"

    monkeypatch.setattr(subprocess, "Popen", Recorder)
    return commands


def config_options(command):
    return [
        value for flag, value in itertools.pairwise(command) if flag == "-c"
    ]


def ssh_command(command):
    commands = [
        value.partition("=")[2]
        for value in config_options(command)
        if value.startswith("core.sshCommand=")
    ]
    return [shlex.split(value) for value in commands]


KEEPALIVE = ["-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]


def assert_fetch_like_libgit2(command):
    assert "maintenance.auto=false" in config_options(command)
    assert "--no-recurse-submodules" in command


def test_git_clone_ssh_passes_ssh_id(
    reset_directory, tmp_path_factory, monkeypatch
):
    workdir = tmp_path_factory.mktemp("ssh-clone-workdir")
    os.chdir(workdir)
    # ssh.id replaces the user's ssh command.
    monkeypatch.setenv("GIT_SSH", "my-ssh")
    commands = record_git(monkeypatch)

    url = "ssh://example.invalid/srv/x.git"
    git = git_project.Git()
    with pytest.raises(git_project.GitProjectError, match="stopped by"):
        git.clone(url, "my key")

    ls_remote, fetch = commands
    for command in commands:
        assert isinstance(command, list)
        assert ssh_command(command) == [
            ["ssh", "-i", str(Path.home() / ".ssh" / "my key"), *KEEPALIVE]
        ]
    assert ls_remote[ls_remote.index("--") + 1 :] == [
        "origin",
        "HEAD",
        "refs/heads/*",
    ]
    assert_fetch_like_libgit2(fetch)


@pytest.mark.parametrize(
    "user_command",
    [
        None,
        "GIT_SSH_COMMAND",
        "GIT_SSH",
        "core.sshCommand",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_COUNT",
    ],
)
def test_git_fetch_remote_ssh_keepalive(
    reset_directory,
    local_repository,
    monkeypatch,
    libgit2_config,
    user_command,
):
    os.chdir(local_repository.path)
    for name in ("GIT_SSH_COMMAND", "GIT_SSH", "GIT_CONFIG_PARAMETERS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    git = git_project.Git()
    git.config.set_item("remote.origin", "url", "example.invalid:/srv/x.git")
    if user_command == "core.sshCommand":
        git.config.set_item("core", "sshCommand", "my-ssh")
    elif user_command == "GIT_CONFIG_PARAMETERS":
        # The form a parent `git -c core.sshCommand=my-ssh` passes.
        monkeypatch.setenv(user_command, "'core.sshcommand'='my-ssh'")
    elif user_command == "GIT_CONFIG_COUNT":
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.sshCommand")
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", "my-ssh")
    elif user_command:
        monkeypatch.setenv(user_command, "my-ssh")
    commands = record_git(monkeypatch)

    with pytest.raises(git_project.GitProjectError, match="stopped by"):
        git.fetch_remote("origin")

    (command,) = commands
    if user_command:
        assert ssh_command(command) == []
    else:
        assert ssh_command(command) == [["ssh", *KEEPALIVE]]
    assert_fetch_like_libgit2(command)


class Libgit2RanError(Exception):
    pass


def no_popen(*args, **kwargs):
    pytest.fail("git ran")


def stop_libgit2(*args, **kwargs):
    raise Libgit2RanError


PASSWORD_URL = "ssh://me:fixture-not-a-secret@example.invalid/srv/x.git"


@pytest.mark.parametrize("operation", ["clone", "fetch"])
def test_git_ssh_password_uses_libgit2(
    reset_directory, local_repository, tmp_path_factory, monkeypatch, operation
):
    monkeypatch.setattr(subprocess, "Popen", no_popen)
    if operation == "clone":
        os.chdir(tmp_path_factory.mktemp("ssh-clone-workdir"))
        git = git_project.Git()
        monkeypatch.setattr(pygit2, "clone_repository", stop_libgit2)
    else:
        os.chdir(local_repository.path)
        git = git_project.Git()
        git.config.set_item("remote.origin", "url", PASSWORD_URL)
        monkeypatch.setattr(pygit2.remotes.Remote, "fetch", stop_libgit2)

    with pytest.raises(Libgit2RanError):
        if operation == "clone":
            git.clone(PASSWORD_URL)
        else:
            git.fetch_remote("origin")


def test_git_fetch_remote_pushurl_only_uses_libgit2(
    reset_directory, local_repository, monkeypatch
):
    os.chdir(local_repository.path)
    git = git_project.Git()
    git.config.set_item("remote.pushonly", "pushurl", "example.invalid:/x.git")
    git.config.set_item(
        "remote.pushonly", "fetch", "+refs/heads/*:refs/remotes/pushonly/*"
    )
    monkeypatch.setattr(subprocess, "Popen", no_popen)
    monkeypatch.setattr(pygit2.remotes.Remote, "fetch", stop_libgit2)

    with pytest.raises(Libgit2RanError):
        git.fetch_remote("pushonly")


def test_git_fetch_remote_ssh_uses_cli(
    reset_directory, local_repository, remote_repository, monkeypatch
):
    os.chdir(local_repository.path)
    use_fake_ssh(local_repository.path, monkeypatch)

    git = git_project.Git()
    url = f"ssh://example.invalid{remote_repository.path}"
    git.config.set_item("remote.origin", "url", url)
    git.set_remote_fetch_refspecs(
        "origin", ["+refs/heads/*:refs/remotes/origin/changed/*"]
    )

    git.fetch_remote("origin")

    refs = list(git.iterrefnames(["refs/remotes/origin/changed"]))
    assert len(refs) > 0


def test_git_ssh_credentials(reset_directory):
    ssh_key = pygit2.enums.CredentialType.SSH_KEY
    username = pygit2.enums.CredentialType.USERNAME

    # A local url authenticates with nothing, so the clone tests above never
    # reach the callback.  Check the credential choice directly instead.
    credentials = git_project.Git._ssh_credentials("id_rsa", "git", ssh_key)

    assert credentials.credential_tuple == (
        "git",
        str(Path.home() / ".ssh" / "id_rsa.pub"),
        str(Path.home() / ".ssh" / "id_rsa"),
        "",
    )

    # Without an ssh ID, a request for only an ssh key is an error.
    with pytest.raises(git_project.GitProjectError, match=r"set ssh\.id\)$"):
        git_project.Git._ssh_credentials(None, "git", ssh_key)

    with pytest.raises(git_project.GitProjectError, match=r"\(no password\)$"):
        git_project.Git._ssh_credentials(None, "git", ssh_key, "no password")

    credentials = git_project.Git._ssh_credentials(
        None, "git", ssh_key | username
    )

    assert credentials.credential_tuple == ("git",)


def test_git_checkout(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.get_committish_oid("HEAD") == git.get_committish_oid("master")

    git.checkout("unmerged")

    assert git.get_committish_oid("HEAD") == git.get_committish_oid("unmerged")

    assert not (
        git.get_committish_oid("master") == git.get_committish_oid("unmerged")
    )

    git.checkout("master")

    assert git.get_committish_oid("HEAD") == git.get_committish_oid("master")

    assert not (
        git.get_committish_oid("master") == git.get_committish_oid("unmerged")
    )


def test_git_checkout_tag_shadows_branch(reset_directory, local_repository):
    os.chdir(local_repository.path)

    master = local_repository.revparse_single("refs/heads/master")
    local_repository.references.create("refs/tags/unmerged", master.id)

    git = git_project.Git()

    git.checkout("unmerged")

    assert git.get_current_refname() == "refs/heads/unmerged"


def test_git_update_symbolic_ref(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    git.update_symbolic_ref("HEAD", "unmerged")

    assert git.get_committish_oid("HEAD") == git.get_committish_oid("unmerged")

    assert not (
        git.get_committish_oid("HEAD") == git.get_committish_oid("master")
    )

    git.update_symbolic_ref("HEAD", "master")

    assert not (
        git.get_committish_oid("HEAD") == git.get_committish_oid("unmerged")
    )

    assert git.get_committish_oid("HEAD") == git.get_committish_oid("master")


def test_git_update_symbolic_ref_tag_shadows_branch(
    reset_directory, local_repository
):
    os.chdir(local_repository.path)

    master = local_repository.revparse_single("refs/heads/master")
    local_repository.references.create("refs/tags/unmerged", master.id)

    git = git_project.Git()

    git.update_symbolic_ref("HEAD", "unmerged")

    assert local_repository.references["HEAD"].target == "refs/heads/unmerged"


def test_git_delete_branch(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    git.create_branch("todelete", "HEAD")

    assert git.committish_exists("todelete")
    assert git.committish_exists("refs/heads/todelete")

    git.delete_branch("todelete")

    assert not git.committish_exists("todelete")
    assert not git.committish_exists("refs/heads/todelete")


def test_git_delete_refname(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    git.create_branch("todelete", "HEAD")

    assert git.committish_exists("todelete")
    assert git.committish_exists("refs/heads/todelete")

    git.delete_branch("refs/heads/todelete")

    assert not git.committish_exists("todelete")
    assert not git.committish_exists("refs/heads/todelete")


def test_git_remote_branch_exists(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.remote_branch_exists("master", "origin")
    assert git.remote_branch_exists("pushed", "origin")
    assert git.remote_branch_exists("notpushed", "origin")
    assert git.remote_branch_exists("merged_remote", "origin")
    assert not git.remote_branch_exists("merged_local", "origin")
    assert not git.remote_branch_exists("unmerged", "origin")


def test_git_remote_branch_exists_timeout(
    reset_directory, local_repository, monkeypatch
):
    os.chdir(local_repository.path)

    git = git_project.Git()
    git.config.set_item("remote.origin", "url", "ssh://example.invalid/x")
    pidfile = Path.cwd() / "ssh.pid"
    ssh = Path.cwd() / "slow-ssh"
    ssh.write_text(f"#!/bin/sh\necho $$ > {pidfile}\nexec sleep 30\n")
    ssh.chmod(0o755)
    monkeypatch.setenv("GIT_SSH_COMMAND", str(ssh))
    monkeypatch.setattr(git_project.Git, "REMOTE_TIMEOUT", 3)

    with pytest.raises(git_project.GitProjectError, match="cannot reach"):
        git.remote_branch_exists("pushed", "origin")

    # The kill reaches ssh, not only git.
    pid = int(pidfile.read_text())
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail("ssh outlived the timeout")


def test_git_delete_remote_branch_timeout_escaped_child(
    reset_directory, local_repository, monkeypatch
):
    os.chdir(local_repository.path)

    git = git_project.Git()
    git.create_branch("todelete", "HEAD")
    # The hook leaves a child in a new session, out of reach of the kill,
    # and the child holds the stdout pipe open.
    escape = "import os, time; os.setsid(); time.sleep(20)"
    hook = Path(git._repo.path) / "hooks" / "pre-push"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text(
        f"#!/bin/sh\n{shlex.quote(sys.executable)} -c '{escape}' &\n"
        "sleep 20\n"
    )
    hook.chmod(0o755)
    monkeypatch.setattr(git_project.Git, "REMOTE_TIMEOUT", 1)

    start = time.monotonic()
    with pytest.raises(git_project.GitProjectError, match="cannot delete"):
        git.delete_remote_branch("todelete", "origin")
    assert time.monotonic() - start < 10


def test_git_remote_branch_exists_no_git(
    reset_directory, local_repository, monkeypatch, tmp_path_factory
):
    os.chdir(local_repository.path)

    git = git_project.Git()
    monkeypatch.setenv("PATH", str(tmp_path_factory.mktemp("empty-path")))

    with pytest.raises(git_project.GitProjectError, match="cannot reach"):
        git.remote_branch_exists("pushed", "origin")


def test_git_remote_git_passes_ssh_id(
    reset_directory, local_repository, monkeypatch
):
    os.chdir(local_repository.path)

    git = git_project.Git()
    git.config.set_item("ssh", "id", "my key")

    commands = []

    class Recorder:
        def __init__(self, command, **kwargs):
            commands.append(command)
            self.returncode = 2

        def communicate(self, timeout=None):
            return "", ""

    monkeypatch.setattr(subprocess, "Popen", Recorder)

    assert not git.remote_branch_exists("pushed", "origin")
    assert commands[0][1] == "-c"
    name, _, value = commands[0][2].partition("=")
    assert name == "core.sshCommand"
    assert shlex.split(value) == [
        "ssh",
        "-i",
        str(Path.home() / ".ssh" / "my key"),
        *KEEPALIVE,
    ]


def test_git_delete_remote_refname(
    reset_directory, local_repository, remote_repository
):
    os.chdir(local_repository.path)

    local_git = git_project.Git()

    os.chdir(remote_repository.path)

    remote_git = git_project.Git()

    assert not local_git.committish_exists("todelete")
    assert not local_git.committish_exists("refs/heads/todelete")

    assert not remote_git.committish_exists("todelete")
    assert not remote_git.committish_exists("refs/heads/todelete")

    local_git.create_branch("todelete", "HEAD")

    assert local_git.committish_exists("todelete")
    assert local_git.committish_exists("refs/heads/todelete")

    local_git._repo.remotes["origin"].push(["refs/heads/todelete"])

    assert remote_git.committish_exists("todelete")
    assert remote_git.committish_exists("refs/heads/todelete")

    assert local_git.committish_exists("refs/remotes/origin/todelete")

    local_git.delete_branch("todelete")

    assert not local_git.committish_exists("todelete")
    assert local_git.committish_exists("refs/remotes/origin/todelete")

    assert remote_git.committish_exists("todelete")
    assert remote_git.committish_exists("refs/heads/todelete")

    local_git.delete_remote_branch("todelete", "origin")

    assert not local_git.committish_exists("refs/remotes/origin/todelete")

    assert not remote_git.committish_exists("todelete")
    assert not remote_git.committish_exists("refs/heads/todelete")


def test_git_detach_head(reset_directory, git):
    git.detach_head()
    assert git.head_is_detached()


def test_git_detach_head_bare(reset_directory, bare_git):
    bare_git.detach_head()
    assert bare_git.head_is_detached()


def test_git_get_remote_fetch_refspecs(reset_directory, git):
    refspecs = git.get_remote_fetch_refspecs("origin")
    # Why this is duplicated is not clear...
    assert refspecs == ["+refs/heads/*:refs/remotes/origin/*"]


def test_git_set_remote_fetch_refspecs(reset_directory, git):
    refspecs = git.get_remote_fetch_refspecs("origin")
    assert refspecs == ["+refs/heads/*:refs/remotes/origin/*"]

    new_refspecs = ["+refs/heads/*:refs/remotes/origin/changed/*"]
    git.set_remote_fetch_refspecs("origin", new_refspecs)

    refspecs = git.get_remote_fetch_refspecs("origin")
    assert refspecs == new_refspecs


def test_git_set_remote_fetch_refspecs_str(reset_directory, git):
    refspecs = git.get_remote_fetch_refspecs("origin")
    assert refspecs == ["+refs/heads/*:refs/remotes/origin/*"]

    new_refspecs = "+refs/heads/*:refs/remotes/origin/changed/*"
    git.set_remote_fetch_refspecs("origin", new_refspecs)

    refspecs = git.get_remote_fetch_refspecs("origin")
    assert refspecs == [new_refspecs]


def test_git_fetch_remote(reset_directory, git):
    new_refspecs = ["+refs/heads/*:refs/remotes/origin/changed/*"]
    git.set_remote_fetch_refspecs("origin", new_refspecs)

    git.fetch_remote("origin")

    refs = list(git.iterrefnames(["refs/remotes/origin/changed"]))
    assert len(refs) > 0


def test_git_iterbranches(reset_directory, git):
    branches = set(git.iterbranches())
    assert branches == {
        "master",
        "merged_local",
        "merged_remote",
        "notpushed",
        "pushed",
        "pushed_indirectly",
        "pushed_remote_only",
        "unmerged",
        "origin/HEAD",
        "origin/master",
        "origin/merged_remote",
        "origin/notpushed",
        "origin/old_master",
        "origin/pushed",
        "origin/remote_only",
    }


def test_git_get_branch_upstream(reset_directory, git):
    master_upstream = git.get_branch_upstream("master")
    assert master_upstream == "origin/master"


def test_git_get_branch_upstream_refname(reset_directory, git):
    master_upstream = git.get_branch_upstream("refs/heads/master")
    assert master_upstream == "origin/master"


def test_git_set_branch_upstream(reset_directory, git):
    assert git.get_branch_upstream("master") == "origin/master"

    git.set_branch_upstream("master", None)

    assert not git.get_branch_upstream("master")

    git.set_branch_upstream("master", "origin/master")

    assert git.get_branch_upstream("master") == "origin/master"


def test_git_get_curent_branch(reset_directory, git):
    assert git.get_current_branch() == "master"


def test_git_workarea_is_clean(reset_directory, git):
    assert git.workarea_is_clean()

    # Remove a file from the index to make it unclean.
    index = git._repo.index
    index.read()

    for entry in index:
        index.remove(entry.path)
        index.write()
        break

    assert not git.workarea_is_clean()


def test_git_get_gitdir(reset_directory, git):
    assert Path(git.get_gitdir()).name == ".git"


def test_git_get_main_branch(reset_directory, git):
    assert git.get_main_branch() == "refs/heads/master"


def test_git_get_main_branch_master_main(reset_directory, git):
    git.create_branch("main", "master")
    assert git.get_main_branch() == "refs/heads/main"


def test_git_get_main_branch_main(reset_directory, git):
    git.create_branch("main", "master")
    git.checkout("main")
    git.delete_branch("master")
    assert git.get_main_branch() == "refs/heads/main"


def test_git_get_main_branch_one_unique(reset_directory, git):
    git.create_branch("newmain", "master")
    git.checkout("newmain")
    for refname in git.iterrefnames(["refs/heads"]):
        if refname != "refs/heads/newmain":
            git.delete_branch(refname)
    assert git.get_main_branch() == "refs/heads/newmain"


def test_git_get_main_branch_no_unique(reset_directory, git):
    git.create_branch("newmain", "master")
    git.checkout("newmain")
    git.delete_branch("master")
    git.create_branch("other", "newmain")

    assert git.get_main_branch() is None


def test_git_get_git_common_dir(reset_directory, git):
    assert Path(git.get_git_common_dir()).name == ".git"


def test_git_get_git_common_dir_worktree(reset_directory, git):
    git.create_branch("test", "master")
    git.add_worktree("test", "../test", "test")

    os.chdir("../test")

    git = git_project.Git()

    assert Path(git.get_git_common_dir()).name == ".git"


def test_git_get_git_common_dir_plain_git_worktree(reset_directory, git):
    common_dir = Path(git.get_gitdir()).resolve()
    git.create_branch("test", "master")
    subprocess.run(["git", "worktree", "add", "../test", "test"], check=True)

    os.chdir("../test")

    git = git_project.Git()

    assert Path(git.get_git_common_dir()) == common_dir


def test_git_worktree_subdir(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    # Create a branch for the worktree.
    commit, _ref = git._repo.resolve_refish("HEAD")
    git._repo.branches.create("user/test-wt", commit)

    worktree_checkout_path = Path.cwd() / ".." / ".." / "user" / "test-wt"

    git.add_worktree("test-wt", str(worktree_checkout_path), "user/test-wt")

    worktree_path = Path(local_repository.path) / "worktrees" / "test-wt"

    assert os.path.exists(worktree_path)
    os.chdir(worktree_path)
    wtgit = git_project.Git()
    assert wtgit.get_current_branch() == "user/test-wt"

    with pytest.raises(
        git_project.GitProjectError,
        match="Will not prune existing worktree test-wt",
    ):
        git.prune_worktree("test-wt")

    shutil.rmtree(worktree_checkout_path)

    git.prune_worktree("test-wt")

    assert not os.path.exists("user/test-wt")


def test_git_worktree_get_current_worktree(reset_directory, local_repository):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    # Create a branch for the worktree.
    commit, _ref = git._repo.resolve_refish("HEAD")
    git._repo.branches.create("user/test-wt", commit)

    worktree_checkout_path = Path.cwd() / ".." / ".." / "user" / "test-wt"

    git.add_worktree("test-wt", str(worktree_checkout_path), "user/test-wt")

    worktree_path = Path(local_repository.path) / "worktrees" / "test-wt"

    assert os.path.exists(worktree_path)

    os.chdir(worktree_checkout_path)

    wtgit = git_project.Git()

    assert wtgit.get_current_worktree() == "test-wt"


def test_git_get_remote_url(
    reset_directory, local_repository, remote_repository
):
    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    url = git.get_remote_url("origin")

    assert url == remote_repository.path


def test_git_reinit(local_repository):
    repo_parent = Path(local_repository.path).parent

    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()
    assert Path(git.get_gitdir()) == Path(local_repository.path)

    new_hidden_dir = ".test.git"

    gitdir = Path(git.get_gitdir())
    newgitdir = repo_parent / new_hidden_dir

    gitdir.rename(newgitdir)

    git.reinit(newgitdir)

    assert git.has_repo()
    assert Path(git.get_gitdir()) == repo_parent / new_hidden_dir


def test_git_get_git_common_dir_renamed(reset_directory, local_repository):
    repo_parent = Path(local_repository.path).parent

    os.chdir(local_repository.path)

    git = git_project.Git()

    assert git.has_repo()

    new_hidden_dir = ".test.git"

    gitdir = Path(git.get_gitdir())
    newgitdir = repo_parent / new_hidden_dir

    gitdir.rename(newgitdir)

    git.reinit(newgitdir)

    assert git.has_repo()
    assert Path(git.get_git_common_dir()).name == new_hidden_dir


def test_git_remote_credentials(reset_directory):
    callback = git_project.Git.RemoteCallbacks(ssh_id="id_rsa")

    key_result = callback.credentials(
        "ssh:me@my.org/test.git", "me", pygit2.enums.CredentialType.SSH_KEY
    )
    name_result = callback.credentials(
        "ssh:me@my.org/test.git", "me", pygit2.enums.CredentialType.USERNAME
    )

    assert isinstance(key_result, pygit2.Keypair)
    assert isinstance(name_result, pygit2.Username)

    no_id = git_project.Git.RemoteCallbacks(ssh_id=None)

    with pytest.raises(git_project.GitProjectError, match=r"ssh\.id"):
        no_id.credentials(
            "ssh:me@my.org/test.git", "me", pygit2.enums.CredentialType.SSH_KEY
        )
