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
from pathlib import Path
import pygit2
import re
import shlex
import subprocess
import urllib

from .exception import GitProjectException
from .shell import capture_command

# Git commands
#
class Git(object):
    """A facade over a lower-level interface to git providing interfaces needed to
    implement git-project functionality."""

    class Config(object):
        """Manage the git config for the current repository."""
        class ConfigSection(object):
            """Managee a specific section of the git config."""
            class ConfigItem(object):
                """Represent a key:value (multi-)pair."""
                def __init__(self, key):
                    self._key = key
                    self._values = set()

                @property
                def key(self):
                    """Return thee key for this entry.  The key is the name within a section for a
                    (multi-)value.

                    """
                    return self._key

                def is_empty(self):
                    """Return whether this key has no values."""
                    return len(self._values) == 0

                def itervalues(self):
                    """Iterate over thee values of a multi-value key."""
                    for value in self._values:
                        yield value

                def get_value(self):
                    """Get the single value of this key.  Raise an exception if there is more than
                    one value."""
                    if self.is_multival():
                        raise GitProjectException('Single value get for multival')
                    return next(iter(self._values))

                def add_value(self, value):
                    """Add a value to this key, potentially turning it into a multi-value key."""
                    self._values.add(value)

                def clear(self):
                    """Remove all values for this key."""
                    self._values.clear()

                def is_multival(self):
                    """Return whether this is a multi-value key."""
                    return len(self._values) > 1

                def remove_value(self, pattern):
                    """Remove the specified value from this key, leaving any other values in place.

                    """
                    self._values = {value for value in self._values
                                    if not re.search(pattern, value)}

            def __init__(self, git, name):
                self._git = git
                self._name = name
                self._items = dict()

            @property
            def name(self):
                """Return the name of this section."""
                return self._name

            def itemname(self, key):
                """Return the full name of a key, including the section."""
                return self.name + '.' + key

            def is_empty(self):
                return len(self._items) == 0

            def set_item(self, key, value):
                """Set key to value."""
                self._git._repo.config[self.itemname(key)] = value
                item = self._items.get(self.itemname(key), None)
                if not item:
                    item = self.ConfigItem(self.itemname(key))
                else:
                    item.clear()

                item.add_value(value)
                self._items[self.itemname(key)] = item

            def add_item(self, key, value):
                """Add a value to the given key, potentially turning it into a multi-value key.

                """
                self._git._repo.config.set_multivar(self.itemname(key), re.escape(value), value)
                item = self._items.get(self.itemname(key), None)
                if not item:
                    item = self.ConfigItem(self.itemname(key))
                item.add_value(value)
                self._items[self.itemname(key)] = item

            def has_item(self, key):
                """Return whether this key exists in this section."""
                return True if self._items.get(self.itemname(key), None) else False

            def get_item(self, key):
                """Get the key:value pair for this key."""
                item = self._items.get(self.itemname(key), None)
                if not item:
                    return None
                return item.get_value()

            def iter_multival(self, key):
                """Iterate over the multiple values of the given key."""
                item = self._items.get(self.itemname(key), None)
                if item:
                    for value in item.itervalues():
                        yield value

            def rm_items(self, key):
                """Remove all values for the given key."""
                del self._git._repo.config[self.itemname(key)]
                del self._items[self.itemname(key)]

            def rm_item(self, key, pattern):
                """Remove all values matching pattern from the given key."""
                item = self._items.get(self.itemname(key), None)
                if not item:
                    return
                item.remove_value(pattern)
                if item.is_empty():
                    del self._items[self.itemname(key)]

                # No pygit2 interface for this.
                capture_command(f'git config --unset {self.itemname(key)} {pattern}')

            # No pygit2 interface for this.
            def rm(self):
                """Remove this entire section from the config."""
                capture_command(f'git config --remove-section {self.name}')

        def __init__(self, git, config):
            self._git = git
            self._sections = dict()

            if self._git.has_repo():
                for entry in config:
                    section, key = entry.name.rsplit('.', 1)
                    section_entry = self.get_section(section)
                    if not section_entry:
                        section_entry = self.ConfigSection(self._git, section)
                    section_entry.add_item(key, entry.value)
                    self._sections[section] = section_entry

        def get_section(self, section):
            """Get the named section from the config."""
            return self._sections.get(section, None)

        def rm_section(self, section_name):
            """Remove the named section from the config."""
            section = self.get_section(section_name)
            if section:
                section.rm()
                del self._sections[section_name]

        def set_item(self, section_name, key, value):
            """Set the value of key under section named by section_name to value."""
            section = self._sections.get(section_name, None)
            if not section:
                section = self.ConfigSection(self._git, section_name)
            section.set_item(key, value)
            self._sections[section_name] = section

        def add_item(self, section_name, key, value):
            """Add the value to key under section named by section_name to value,
            potentially turning it into a multi-value key.

            """
            section = self._sections.get(section_name, None)
            if not section:
                section = self.ConfigSection(self._git, section_name)
            section.add_item(key, value)
            self._sections[section_name] = section

        def iter_multival(self, section_name, key):
            """Iterate over the multiple values of the given multi-value key."""
            section = self.get_section(section_name)
            if section:
                for value in section.iter_multival(key):
                    yield value

        def has_item(self, section_name, key):
            """Return whether the named section has key in it."""
            section = self.get_section(section_name)
            if not section:
                return False
            return section.has_item(key)

        def get_item(self, section_name, key):
            """Get the valuee of the key in the named section."""
            section = self.get_section(section_name)
            if not section:
                return None
            return section.get_item(key)

        def rm_items(self, section_name, key):
            """Remove all values of the key in the named section."""
            section = self.get_section(section_name)
            if not section:
                return

            section.rm_items(key)

            if section.is_empty():
                del self._sections[section_name]

        def rm_item(self, section_name, key, pattern):
            """Remove all values matching pattern from the key in the named section."""
            section = self.get_section(section_name)
            if not section:
                return

            section.rm_item(key, pattern)

            if section.is_empty():
                del self._sections[section_name]

    class RemoteBranchDeleteCallback(pygit2.RemoteCallbacks):
        """Check the result of remove branch prune operations."""
        def push_update_reference(self, refname, message):
            if message is not None:
                raise GitProjectException('Could not prune remote branch: {}'.
                                format(message))

    class LsRemotesCallbacks(pygit2.RemoteCallbacks):
        def credentials(self, url, username_from_url, allowed_types):
            if allowed_types & pygit2.credentials.GIT_CREDENTIAL_SSH_KEY:
                return pygit2.Keypair(username_from_url, str(Path.home() / '.ssh' / 'id_rsa.pub'),
                                      str(Path.home() / '.ssh' / 'id_rsa'), '')
            elif allowed_types & pygit2.credentials.GIT_CREDENTIAL_USERNAME:
                return pygit2.Username(username_from_url)
            return None

    # Repository-wide info
    def __init__(self):
        repo_path = pygit2.discover_repository(Path.cwd())
        if repo_path:
            self._repo = pygit2.Repository(repo_path)
            self._config = self.Config(self, self._repo.config)

    @property
    def config(self):
        """Return the config of the repository."""
        return self._config

    def has_repo(self):
        """Return whether we are attached to a repository."""
        return hasattr(self, '_repo')

    def is_bare_repository(self):
        """Return whether the configured repository is bare."""
        return self._repo.is_bare

    def get_working_copy_root(self):
        """Get the root of the current working copy."""
        cwd = Path.cwd().resolve()

        # See if this is a worktree.
        for name in self._repo.list_worktrees():
            worktree = self._repo.lookup_worktree(name)
            path = Path(worktree.path).resolve()
            if path == cwd or cwd.is_relative_to(path):
                return str(path)

        # See if we have a GITDIR somewhere along the way.
        gitdir = Path(self._repo.path).resolve()
        while True:
            if gitdir != cwd and gitdir.is_relative_to(cwd):
                return cwd
            parent = cwd.parent
            if parent == cwd:
                break
            cwd = parent

        # We didn't find a matching worktree or a gitdir relative to the current
        # path.  Gibe up.
        return None

    def get_current_refname(self):
        """Get the refname of HEAD."""
        reference = self._repo.lookup_reference_dwim('HEAD')
        return reference.name

    # Low-level committish info, can be branches, hashes, etc.

    def committish_to_ref(self, committish):
        """Translate a committish to a reference object."""
        commit, ref = self._repo.resolve_refish(committish)
        return ref


    def committish_to_refname(self, committish):
        """Translate a committish to a refname."""
        return self.committish_to_ref(committish).name

    def get_committish_commit(self, committish):
        """Get the commit object for a committish."""
        commit = self._repo.revparse_single(committish)
        return commit

    def get_committish_oid(self, committish):
        """Get an opaque object id of a committish commit."""
        return self.get_committish_commit(committish).id

    def committish_exists(self, committish):
        """Return whether the committish exists in the repository."""
        try:
            self._repo.revparse_single(committish)
            return True
        except:
            return False

    def is_strict_ancestor(self, committish, descendant):
        """Return whether the given committish is an ancestor of the given descendant
        committish.  If committish and descendant are the same there is no
        ancestor relationship.

        """
        committish_oid = self._repo.revparse_single(committish).id
        descendant_oid = self._repo.revparse_single(descendant).id
        return self._repo.descendant_of(descendant_oid, committish_oid)

    # Info on refs.

    @staticmethod
    def refname_to_branch_name(refname):
        """Translate a refname to a branch name."""
        prefix = 'refs/heads/'
        if refname.startswith(prefix):
            return refname[len(prefix):]
        return refname

    @staticmethod
    def branch_name_to_refname(branch_name):
        """Translate a branch name to a refname."""
        prefix = 'refs/heads/'
        if branch_name.startswith(prefix):
            return branch_name
        return prefix + branch_name

    def get_remote_fetch_refname(self, refname, remote):
        """Get the refname on the remote side for a fetch of the given local refname."""
        # FIXME: pygit2 should expose this.
        fetch_direction = 0
        remote = self._repo.remotes[remote]
        for refspec_id in range(0, remote.refspec_count):
            refspec = remote.get_refspec(refspec_id)
            if refspec.direction == fetch_direction and refspec.src_matches(refname):
                remote_refname = refspec.transform(refname)
                return remote_refname

        return None

    def get_remote_push_refname(self, refname, remote):
        """Get the refname on the remote side for a push of the given local refname."""
        # FIXME: pygit2 should expose this.
        push_direction = 1
        remote = self._repo.remotes[remote]
        for refspec_id in range(0, remote.refspec_count):
            refspec = remote.get_refspec(refspec_id)
            if refspec.direction == push_direction and refspec.src_matches(refname):
                remote_refname = refspec.transform(refname)
                return remote_refname

        return None

    def get_remote_fetch_refname_oid(self, refname, remote):
        """Get the opaque object ID of the remote fetch refname of the given local
        refname."""
        remote_refname = self.get_remote_fetch_refname(refname, remote)
        if remote_refname:
            return self.get_committish_oid(remote_refname)

        return None

    def get_remote_push_refname_oid(self, refname, remote):
        """Get the opaque object ID of the remote push refname of the given local
        refname."""
        remote_refname = self.get_remote_push_refname(refname, remote)
        if remote_refname:
            return self.get_committish_oid(remote_refname)

        return None

    def committish_is_pushed(self, committish, remote):
        """Return whether the given committish is pushed to the given remote.  If the
        given committish has no remote refname, it is not considered pushed,
        though note that the commits pointed to by commitish may in fact exist
        on the remote under another branch.

        """
        local_oid = self.get_committish_oid(committish)
        refname = self.committish_to_refname(committish)
        remote_refname = self.get_remote_push_refname(refname, remote)
        if not self.committish_exists(remote_refname):
            return False
        remote_oid = self.get_committish_oid(remote_refname)
        if remote_oid:
            if local_oid == remote_oid or self._repo.descendant_of(remote_oid,
                                                                   local_oid):
                # local_oid is reachable from remote_oid,
                return True

        return False

    def refname_is_merged(self, refname, target):
        """Return whether commits pointed to by the given refname are accessible from
        the given target committish.

        """
        ref_oid = self.get_committish_oid(refname)
        target_oid = self.get_committish_oid(target)
        return ref_oid == target_oid or self._repo.descendant_of(target_oid, ref_oid)

    def iterrefnames(self, patterns):
        """Iterate over all of the refnames matching the given pattern."""
        for refname in self._repo.references:
            for pattern in patterns:
                if refname.startswith(pattern):
                    yield refname

    # Higher-level commands.

    def create_branch(self, branch_name, committish):
        """Create a branch with the given name pointing to committish."""
        commit = self.get_committish_commit(committish)
        # Just in case
        branch_name = self.refname_to_branch_name(branch_name)
        self._repo.branches.create(branch_name, commit)

    def clone (self, url, bare=False, callbacks=None):
        """Clone a respository at the given url, making a bare clone if specified."""
        parsed_url = urllib.parse.urlparse(url)
        path = Path(parsed_url.path).resolve()
        name = path.name
        target_path = str(Path.cwd() / name)
        self._repo = pygit2.clone_repository(url, target_path, bare, callbacks=callbacks)
        self._config = self.Config(self, self._repo.config)

        return str(Path(target_path).resolve())

    def checkout(self, committish):
        """Make the given committish active in the current worktree."""
        refname = self.committish_to_refname(committish)
        self._repo.checkout(refname)

    def add_worktree(self, name, path, committish):
        """Add a worktree at the given path pointing to the given committish.  Name it
        with the given name to use as a handle.

        """
        ref = self.committish_to_ref(committish)
        self._repo.add_worktree(name, path, ref)

    def prune_worktree(self, name):
        """Remove the given worktree if its working copy has been deleted.  Raise an
        exception if the working copy still exists.

        """
        worktree = self._repo.lookup_worktree(name)
        if os.path.exists(worktree.path):
            raise GitProjectException('Will not prune existing worktree {name}')

        # Prune the worktree. For some reason, libgit2 treats a worktree as
        # valid unless both the worktree directory and data dir under
        # $GIT_DIR/worktrees are gone. This doesn't make much sense since the
        # normal usage involves removing the worktree directory and then
        # pruning. So, for now we have to force the prune. This may be something
        # to take up with libgit2.
        worktree.prune(True)

    def update_symbolic_ref(self, name, committish):
        """Make symbolic ref name point to committish.  This is primarily used to update
        HEAD.

        """
        ref = self._repo.references.get(name)
        refname = self.committish_to_refname(committish)
        if ref:
            ref.set_target(refname,
                           'Reset {} to {} for worktree'.format(name,
                                                                committish))

    def delete_branch(self, branch_name):
        """Delete the named branch."""
        # TODO: Check that it's actually a branch.
        self._repo.branches.delete(branch_name)

    def remote_branch_exists(self, branch_name, remote):
        """Return whethe the given branch exists on the given remote."""
        refname = self.branch_name_to_refname(branch_name)
        # FIXME: This is likely to be something like
        # refs/remotes/<remote>/<branch_name> but that is not what it's called
        # in the ls_remotes call.  There doesn't seem to be a way to get the
        # (local) name of the branch on the remote side.  Assume for now that
        # it's the same as our local name.
        remote_refname = self.get_remote_push_refname(refname, remote)
        for item in self._repo.remotes[remote].ls_remotes(callbacks=Git.LsRemotesCallbacks()):
            if not item['local'] and item['name'] == refname:
                return True
        return False

    def delete_remote_branch(self, branch_name, remote):
        """Remove the given local branch from the given remote."""
        # FIXME: What if the remote branch is not in refs/heads?  For some
        # reason push :branch_name doesn't work.  push
        # :remotes/<remote>/branch_name also doesn't work.
        refname = self.branch_name_to_refname(branch_name)
        callback = self.RemoteBranchDeleteCallback();
        refspecs = [f':{refname}']
        remote = self._repo.remotes[remote]
        remote.push(refspecs, callback)
