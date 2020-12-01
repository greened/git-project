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

from pathlib import Path

from .git import Git
from .scopedobj import ScopedConfigObject

class Project(ScopedConfigObject):
    """A class representing a project section in the git config.  Each invocation of
    git-project has an 'active project' determined by the name through which
    git-project was invoked.  An invocation of 'git-project' makes 'project' the
    active project while an invocation via a link will make the link name the
    active project.  For example a link named 'git-fizzbin' would make "fizzbin'
    the active project.

    """

    def __init__(self, git, section, subsection, ident, **kwargs):
        """Project construction.  This should be treated as a private method and all
        construction should occur through the get method.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        super().__init__(git, section, subsection, ident, **kwargs)

        self.set_defaults()

    @classmethod
    def get(cls, git, section, **kwargs):
        """A factory to construct the active project from its git config.

        cls: The derived class being constructed.

        git: An object to query the repository and make config changes.

        section: git config for this Project.

        """
        project = super().get(git,
                              section,
                              None,
                              None,
                              **kwargs)
        return project

    def set_defaults(self):
        if self._git.has_repo():
            if not self.has_item('branch'):
                self.branch = 'master'
            if not self.has_item('remote'):
                self.remote = 'origin'

    def add_remote(self, remote):
        """Add a remote for this project.  All branches for this project are checked
        against all remotes for the project to determine their pushed state.  A
        branch prune is allowed for any merged branch whose target has been
        pushed to at least one remote..

        remote: The remote to add.

        """
        self.add_item('remote', remote)

    def iterremotes(self):
        """Iterate over the remotes for this project."""
        for remote in self.iter_multival('remote'):
            yield remote

    def add_branch(self, branch):
        """Add a branch for this project.  Project branches are considered to be
        'authoritative' for the project, in that branch merge checks are made
        against each project branch.  On other words a branch is considered
        'finished' if it is merged to a project branch and that branch has been
        pushed to a project remote."  self.add_item('branch', branch)

        branch: The branch to add.

        """
        self.add_item('branch', branch)

    def iterbranches(self):
        """Iterate over the project's branches."""
        for branch in self.iter_multival('branch'):
            yield branch

    # Git interface customized to project.

    # Ref info.

    def iterrefnames(self):
        """Iterate over all of the refnames for project branches and remotes.  This is
        used to check for merged and pushed status o branches.

        """
        if self._git.has_repo():
            for branch in self._git.iterrefnames(['refs/heads/{0}'.format(branch) for branch in self.iterbranches()] +
                                                 ['refs/remotes/{0}/{1}'.
                                                  format(remote, branch) for branch in
                                                  self.iterbranches() for remote in
                                                  self.iterremotes()]):
                yield branch.strip()

    # Branch info.

    def branch_is_merged(self, committish):
        """Return whether the given committish is merged to a project branch.

        committish: The committish to check

        """
        for branch in self.iterbranches():
            if self._git.refname_is_merged(committish, branch):
                return True
        return False

    def branch_is_pushed(self, committish):
        """Return whether a given committish is pushed to the remote.  This tests
        whether the commit at committish is pushed.  This will return true if
        the committish itself is pushed or if the given committish is merged to
        a project branch and that project branch is pushed.

        committish: The committish to check.

        """
        for remote in self.iterremotes():
            if self._git.committish_is_pushed(committish, remote):
                return True
        # Not directly pushed, see if it is pushed as part of a merge.
        refname = self._git.committish_to_refname(committish)
        for target in self.iterbranches():
            target_refname = self._git.committish_to_refname(target)
            for remote in self.iterremotes():
                target_remote_refname = self._git.get_remote_push_refname(target_refname, remote)
                if not target_remote_refname:
                    continue
                if self._git.refname_is_merged(refname, target_remote_refname):
                    return True
        return False

    # Higher-level commands

    def prune_branch(self, branch):
        """Delete a branch, both locally and on any remotes on which it exists.

        branch: The branch to delete.

        """
        for remote in self.iterremotes():
            if self._git.remote_branch_exists(branch, remote):
                self._git.delete_remote_branch(branch, remote)
        if self._git.committish_exists(branch):
            self._git.delete_branch(Git.refname_to_branch_name(branch))
