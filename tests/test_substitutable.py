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
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License along
# with git-project. If not, see <https://www.gnu.org/licenses/>.

import os
from pathlib import Path

import pytest

import git_project
from git_project.test_support import check_config_file


class MySubstitutable(git_project.SubstitutableConfigObject):
    def __init__(self, git, project_section, subsection, ident, **kwargs):
        super().__init__(git, project_section, subsection, ident, **kwargs)

    @classmethod
    def get(cls, git, project_section, ident):
        return super().get(
            git,
            project_section,
            "mysubstitutable",
            ident,
            command="cd {builddir}/{branch} && make {target}",
            description="Test command",
        )


class MyNoBranchSubstitutable(git_project.SubstitutableConfigObject):
    def __init__(self, git, project_section, subsection, ident, **kwargs):
        super().__init__(git, project_section, subsection, ident, **kwargs)

    @classmethod
    def get(cls, git, project_section, ident):
        return super().get(
            git,
            project_section,
            "mysubstitutable",
            ident,
            command="cd {builddir} && make {target}",
            description="Test command",
        )


def test_substitutable_get(reset_directory, git):
    substitutable = MySubstitutable.get(git, "project", "test")

    assert substitutable.command == "cd {builddir}/{branch} && make {target}"


def test_substitutable_substitute_command(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {project.builddir}/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_command_recursive(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build/{target}",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd /path/to/build/{project.target}/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_command_no_dup(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build/{target}",
                target="install",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    project.build = "devrel"
    project.add_item("build", "check-devrel")

    check_config_file(
        "project.myproject", "builddir", {"/path/to/build/{target}"}
    )

    check_config_file("project.myproject", "target", {"install"})

    check_config_file("project.myproject", "build", {"devrel", "check-devrel"})

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd /path/to/build/{project.target}/{git.get_current_branch()} && make {project.target}"
    )

    check_config_file(
        "project.myproject", "builddir", {"/path/to/build/{target}"}
    )

    check_config_file("project.myproject", "target", {"install"})

    check_config_file("project.myproject", "build", {"devrel", "check-devrel"})


def test_substitutable_substitute_command_subsection(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build",
                target="{mysubstitutable}",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    project.mysubstitutable = "test"

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {project.builddir}/{git.get_current_branch()} && make {project.mysubstitutable}"
    )


def test_substitutable_substitute_project_in_target(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build",
                target="{mysubstitutable} {project}",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    project.mysubstitutable = "test"

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {project.builddir}/{git.get_current_branch()} && make {project.mysubstitutable} {project.get_section()}"
    )


def test_substitutable_substitute_scope(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build/{worktree}",
                target="{mysubstitutable} {project}",
            )

    class MyWorktree(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git, "project", "worktree", "myworktree")

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()
    worktree = MyWorktree()

    project.push_scope(worktree)

    project.mysubstitutable = "test"

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd /path/to/build/myworktree/{git.get_current_branch()} && make {project.mysubstitutable} {project.get_section()}"
    )


def test_substitutable_substitute_formats(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build",
                target="debug {options}",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    formats = {"options": "opt"}

    command = substitutable.substitute_value(
        git, project, substitutable.command, formats
    )

    assert (
        command
        == f"cd {project.builddir}/{git.get_current_branch()} && make debug opt"
    )


def test_substitutable_substitute_gitdir_with_formats(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{gitdir}/../../path/to/build",
                target="debug {options}",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    formats = {"options": "opt"}

    command = substitutable.substitute_value(
        git, project, substitutable.command, formats
    )

    assert (
        command
        == f"cd {git.get_gitdir()}/../../path/to/build/{git.get_current_branch()} && make debug opt"
    )


def test_substitutable_substitute_git_common_dir_with_formats(
    reset_directory, git
):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{git_common_dir}/../../path/to/build",
                target="debug {options}",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    formats = {"options": "opt"}

    command = substitutable.substitute_value(
        git, project, substitutable.command, formats
    )

    assert (
        command
        == f"cd {git.get_git_common_dir()}/../../path/to/build/{git.get_current_branch()} && make debug opt"
    )


def test_substitutable_substitute_substitutable_item(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git, "project", None, "myproject")

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, "echo {description}"
    )

    assert command == f"echo {substitutable.description}"


def test_substitutable_substitute_command_rebase(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    git.checkout("notpushed")
    current_branch = git.get_current_branch()

    os.chdir(git.get_working_copy_root())
    git_project.run_command_with_shell("git rebase --exec false origin/master")

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {project.builddir}/{current_branch} && make {project.target}"
    )


def test_substitutable_substitute_command_rebase_worktree(
    reset_directory, git
):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    # Create a branch for the worktree.
    commit, _ref = git._repo.resolve_refish("HEAD")
    git._repo.branches.create("user/test-subst", commit)

    worktree_checkout_path = Path.cwd() / ".." / ".." / "user" / "test-subst"

    git.add_worktree(
        "test-subst", str(worktree_checkout_path), "user/test-subst"
    )

    os.chdir(worktree_checkout_path)

    wtgit = git_project.Git()

    current_branch = wtgit.get_current_branch()

    git_project.run_command_with_shell("git rebase --exec false origin/master")

    command = substitutable.substitute_value(
        wtgit, project, substitutable.command
    )

    assert (
        command
        == f"cd {project.builddir}/{current_branch} && make {project.target}"
    )


def test_substitutable_substitute_expression_stays_literal(
    reset_directory, git
):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    # Create a branch.
    commit, _ref = git._repo.resolve_refish("HEAD")
    git._repo.branches.create("imerge/user/test-fstr", commit)

    git.checkout("imerge/user/test-fstr")

    git_project.run_command_with_shell("git rebase --exec false origin/master")

    command = substitutable.substitute_value(
        git, project, "cd {builddir}/{branch}"
    )

    assert command == "cd /path/to/build/imerge/user/test-fstr"

    substitutable.command = (
        'cd {builddir}/{branch.replace("imerge/", "", 1)} && make {target}'
    )

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert command == (
        'cd /path/to/build/{branch.replace("imerge/", "", 1)} && make debug'
    )


def test_substitutable_substitute_recursive(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/{builddir}",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    with pytest.raises(RuntimeError, match="Recursive substitution"):
        substitutable.substitute_value(git, project, substitutable.command)


def test_substitutable_substitute_project(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="/path/to/build/{project}",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd /path/to/build/{project.get_section()}/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_gitdir(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{gitdir}/../path/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {git.get_gitdir()}/../path/to/build/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_git_common_dir(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{git_common_dir}/../path/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {git.get_git_common_dir()}/../path/to/build/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_git_workdir(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{git_workdir}/path/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {git.get_working_copy_root()}/path/to/build/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_escaped_braces(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{git_workdir}/{{}path{}}/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {git.get_working_copy_root()}/{{path}}/to/build/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_preserve_escaped_braces(
    reset_directory, git
):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{git_workdir}/{{}{{}{}}path{{}{}}{}}/to/build",
                target="debug",
            )

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyProject()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {git.get_working_copy_root()}/{{{{}}path{{}}}}/to/build/{git.get_current_branch()} && make {project.target}"
    )


def test_substitutable_substitute_no_branch(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(
                git,
                "project",
                None,
                "myproject",
                builddir="{git_workdir}/path/to/build",
                target="debug",
            )

    substitutable = MyNoBranchSubstitutable.get(git, "project", "test")

    project = MyProject()

    git.detach_head()

    command = substitutable.substitute_value(
        git, project, substitutable.command
    )

    assert (
        command
        == f"cd {git.get_working_copy_root()}/path/to/build && make {project.target}"
    )


def test_substitutable_substitute_formats_not_shared(reset_directory, git):
    class MyProject(git_project.ScopedConfigObject):
        def __init__(self):
            super().__init__(git, "project", None, "myproject")

    project = MyProject()

    first = git_project.SubstitutableConfigObject(
        git, "project", "mysub", "first", leaked="first"
    )
    second = git_project.SubstitutableConfigObject(
        git, "project", "mysub", "second"
    )

    formats = {}
    assert first.substitute_value(git, project, "{leaked}", formats) == "first"
    assert formats == {}

    assert first.substitute_value(git, project, "{leaked}") == "first"

    # The second object has no leaked item, so it cannot see the first's.
    with pytest.raises(NameError):
        second.substitute_value(git, project, "{leaked}")


class MyTargetProject(git_project.ScopedConfigObject):
    def __init__(self, git):
        super().__init__(
            git,
            "project",
            None,
            "myproject",
            builddir="/path/to/build",
            target="debug",
        )


def substitute(git, string):
    substitutable = MySubstitutable.get(git, "project", "test")
    project = MyTargetProject(git)
    return substitutable.substitute_value(git, project, string)


def test_substitutable_substitute_no_code_execution(
    reset_directory, git, tmp_path
):
    pwned = tmp_path / "pwned"
    value = f'{{__import__("os").system("touch {pwned}")}}'

    assert substitute(git, value) == value
    assert not pwned.exists()


def test_substitutable_substitute_single_quote(reset_directory, git):
    assert substitute(git, "echo '{target}'") == "echo 'debug'"


@pytest.mark.parametrize(
    "value",
    [
        "{target.upper()}",
        "{target[0]}",
        "{target.__class__}",
        "{target!r}",
        "{target:>8}",
        "{1+1}",
        "{ target }",
    ],
    # The fixtures put the test id in a repo path, so keep it plain.
    ids=["call", "index", "attribute", "conversion", "spec", "sum", "spaces"],
)
def test_substitutable_substitute_attribute_index_spec_literal(
    reset_directory, git, value
):
    assert substitute(git, value) == value


@pytest.mark.parametrize(
    "value, expected",
    [
        ("awk '{print $1}' {target}", "awk '{print $1}' debug"),
        (r"find . -exec echo {} \;", r"find . -exec echo {} \;"),
        ("a { b", "a { b"),
        ("a } b", "a } b"),
    ],
    # The fixtures put the test id in a repo path, so keep it plain.
    ids=["awk", "empty", "open", "close"],
)
def test_substitutable_substitute_stray_braces_literal(
    reset_directory, git, value, expected
):
    assert substitute(git, value) == expected


def test_substitutable_substitute_escaped_name_not_substituted(
    reset_directory, git
):
    assert substitute(git, "{{}target{}}") == "{target}"


def test_substitutable_substitute_doubled_braces(reset_directory, git):
    assert substitute(git, "{{target}}") == "debug"


def test_substitutable_substitute_sentinel_text_literal(reset_directory, git):
    assert substitute(git, "[[[x]]] {{}y{}}") == "[[[x]]] {y}"


def test_substitutable_substitute_two_scopes_one_pass(reset_directory, git):
    class MyScope(git_project.ScopedConfigObject):
        def __init__(self, subsection, ident):
            super().__init__(git, "project", subsection, ident)

    substitutable = MySubstitutable.get(git, "project", "test")

    project = MyTargetProject(git)
    project.push_scope(MyScope("worktree", "myworktree"))
    project.push_scope(MyScope("build", "mybuild"))

    command = substitutable.substitute_value(
        git, project, "{worktree}/{build}"
    )

    assert command == "myworktree/mybuild"
