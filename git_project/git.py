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
import progressbar
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

    class RemoteCallbacks(pygit2.RemoteCallbacks):
        def __init__(self):
            self.progress = progressbar.ProgressBar()

            self.started_transfer = False
            self.transfer_done = False

            self.started_deltas = False
            self.deltas_done = False

            self.null_oid = pygit2.Oid(hex='0000000000000000000000000000000000000000')

        def credentials(self, url, username_from_url, allowed_types):
            if allowed_types & pygit2.credentials.GIT_CREDENTIAL_SSH_KEY:
                return pygit2.Keypair(username_from_url, str(Path.home() / '.ssh' / 'id_rsa.pub'),
                                      str(Path.home() / '.ssh' / 'id_rsa'), '')
            elif allowed_types & pygit2.credentials.GIT_CREDENTIAL_USERNAME:
                return pygit2.Username(username_from_url)
            return None

        def sideband_progress(self, message):
            print(f'Remote: {message}')

        def transfer_progress(self, stats):
            if not self.started_transfer:
                self.started_transfer = True
                print(f'Receiving objects ({stats.total_objects})...')
                self.progress.start(stats.total_objects)

            if not self.transfer_done:
                self.progress.update(stats.received_objects)
                if stats.received_objects >= stats.total_objects:
                    self.progress.finish()
                    self.transfer_done = True

            if stats.total_deltas > 0 and not self.started_deltas:
                self.started_deltas = True
                print(f'Resolving deltas ({stats.total_deltas})...')
                self.progress.start(stats.total_deltas)

            if self.started_deltas and not self.deltas_done:
                self.progress.update(stats.indexed_deltas)
                if stats.indexed_deltas >= stats.total_deltas:
                    self.progress.finish()
                    self.deltas_done = True
                    print('')

        def update_tips(self, refname, old, new):
            if old != self.null_oid:
                print(f'{refname} {str(old)} -> {str(new)}')
            else:
                print(f'{refname} -> {str(new)}')

    class Config(object):
        """Manage the git config for the current repository."""
        class ConfigSection(object):
            """Manage a specific section of the git config."""
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

                def has_value(self, value):
                    """Return whether the given value is in the item."""
                    return value in self._values

                def add_value(self, value):
                    """Add a value to this key, potentially turning it into a multi-value key."""
                    assert not value in self._values
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

            def __init__(self, git, name, content_dict):
                self._git = git
                self._name = name
                self._items = dict()
                for key, values in content_dict.items():
                    config_item = self.ConfigItem(self.itemname(key))
                    for value in values:
                        config_item.add_value(value)
                    self._items[self.itemname(key)] = config_item

            @property
            def name(self):
                """Return the name of this section."""
                return self._name

            def __iter__(self):
                yield from self._items.items()

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
                if self.has_value(key, value):
                    return

                self._git._repo.config.set_multivar(self.itemname(key), re.escape(value), value)
                item = self._items.get(self.itemname(key), None)
                if not item:
                    item = self.ConfigItem(self.itemname(key))
                item.add_value(value)
                self._items[self.itemname(key)] = item

            def has_item(self, key):
                """Return whether this key exists in this section."""
                return True if self._items.get(self.itemname(key), None) else False

            def has_value(self, key, value):
                """Return whether this key with this values exists in this section."""
                item = self._items.get(self.itemname(key), None)
                if not item:
                    return False
                return item.has_value(value)

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
                del self._items[self.itemname(key)]
                # No pygit2 interface for this.
                prev_dir = Path.cwd()
                os.chdir(self._git._repo.path)
                capture_command(f'git config --unset-all {self.itemname(key)}')
                os.chdir(prev_dir)

            def rm_item(self, key, pattern):
                """Remove all values matching pattern from the given key."""
                item = self._items.get(self.itemname(key), None)
                if not item:
                    return
                item.remove_value(pattern)
                if item.is_empty():
                    del self._items[self.itemname(key)]

                # No pygit2 interface for this.
                prev_dir = Path.cwd()
                os.chdir(self._git._repo.path)
                capture_command(f'git config --unset {self.itemname(key)} {pattern}')
                os.chdir(prev_dir)

            # No pygit2 interface for this.
            def rm(self):
                """Remove this entire section from the config."""
                capture_command(f'git config --remove-section {self.name}')

        def __init__(self, git, config):
            self._git = git
            self._sections = dict()

            if self._git.has_repo():
                # First gather the contents of each section.  We do it this way
                # because iteratively adding key, value means will will call
                # add_entry for each item.  Since the underlying config already
                # contains everything, we don't want to call add_entry again and
                # add duplicates.  So we call a proper ConfigSection
                # intialization after gathering all the entries.
                sections = dict()
                for entry in config:
                    section, key = entry.name.rsplit('.', 1)
                    if not section in sections:
                        sections[section] = dict()
                    section_entry = sections[section]
                    if not key in section_entry:
                        section_entry[key] = set()
                    section_entry[key].add(entry.value)

                self._git.validate_config()
                for section_name, section_dict in sections.items():
                    config_section = self.ConfigSection(self._git,
                                                        section_name,
                                                        section_dict)
                    self._sections[section_name] = config_section
                self._git.validate_config()

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
                section = self.ConfigSection(self._git, section_name, dict())
            section.set_item(key, value)
            self._sections[section_name] = section

        def add_item(self, section_name, key, value):
            """Add the value to key under section named by section_name to value,
            potentially turning it into a multi-value key.

            """
            section = self._sections.get(section_name, None)
            if not section:
                section = self.ConfigSection(self._git, section_name, dict())
            if not section.has_value(key, value):
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
        def credentials(self, url, username_from_url, allowed_types):
            if allowed_types & pygit2.credentials.GIT_CREDENTIAL_SSH_KEY:
                return pygit2.Keypair(username_from_url, str(Path.home() / '.ssh' / 'id_rsa.pub'),
                                      str(Path.home() / '.ssh' / 'id_rsa'), '')
            elif allowed_types & pygit2.credentials.GIT_CREDENTIAL_USERNAME:
                return pygit2.Username(username_from_url)
            return None

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
            self.validate_config()

    @property
    def config(self):
        """Return the config of the repository."""
        return self._config

    def has_repo(self):
        """Return whether we are attached to a repository."""
        return hasattr(self, '_repo')

    def reload_config(self):
        """Reload the config."""
        if self.has_repo():
            self._config = self.Config(self, self._repo.config)

    def is_bare_repository(self):
        """Return whether the configured repository is bare."""
        return self._repo.is_bare

    def workarea_is_clean(self):
        if self.is_bare_repository():
            return True

        status = self._repo.status()
        for filepath, flags in status.items():
            if flags != pygit2.GIT_STATUS_CURRENT:
                return False

        return True

    def get_gitdir(self):
        """Get the GITDIR directory."""
        return self._repo.path

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

    # Operations on remotes

    def set_remote_fetch_refspecs(self, remote, refspecs):
        """Set the refspec list for the given remote to refspecs."""
        if isinstance(refspecs, str):
            refspecs = [refspecs]

        self.config.rm_items(f'remote.{remote}', 'fetch')
        for refspec in refspecs:
            self._repo.remotes.add_fetch(remote, refspec)

    def get_remote_fetch_refspecs(self, remote):
        """Get the list of refspecs for the given remote."""
        return self._repo.remotes[remote].fetch_refspecs

    def fetch_remote(self, remote):
        """Fetch all refspecs from the given remote."""
        callbacks = Git.RemoteCallbacks()
        self._repo.remotes[remote].fetch(callbacks=callbacks)

    # Info on refs.

    @staticmethod
    def refname_to_branch_name(refname):
        """Translate a refname to a branch name."""
        prefix = 'refs/heads/'
        if refname.startswith(prefix):
            return refname[len(prefix):]
        prefix = 'refs/remotes/'
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
        if isinstance(patterns, str):
            patterns = [patterns]

        for refname in self._repo.references:
            for pattern in patterns:
                if refname.startswith(pattern):
                    yield refname

    def iterbranches(self):
        """Iterate over all of the repository's branches."""
        for branch in self._repo.branches:
            yield branch

    # Higher-level commands.

    def detach_head(self):
        """Cause HEAD to be detached."""
        head_ref = self.get_committish_commit('HEAD')
        if not self.is_bare_repository():
            self._repo.checkout_tree(head_ref)
        self._repo.set_head(head_ref.id)

    def head_is_detached(self):
        """Return whether HEAD is detched."""
        return self._repo.head_is_detached

    def create_branch(self, branch_name, committish):
        """Create a branch with the given name pointing to committish."""
        commit = self.get_committish_commit(committish)
        # Just in case
        branch_name = self.refname_to_branch_name(branch_name)
        self._repo.branches.create(branch_name, commit)

    def get_current_branch(self):
        """Get the currently-checked-out branch."""
        if self.head_is_detached():
            return None
        return self.refname_to_branch_name(self.get_current_refname())

    def set_branch_upstream(self, branch_name, remote_branch_name):
        """Set the upstream of branch_name to remote_branch_name."""
        branch_name = self.refname_to_branch_name(branch_name)
        if remote_branch_name:
            remote_branch_name = self.refname_to_branch_name(remote_branch_name)

        branch = self._repo.branches[branch_name]

        remote_branch = None
        if remote_branch_name:
            remote_branch = self._repo.branches[remote_branch_name]

        branch.upstream = remote_branch

    def get_branch_upstream(self, branch_name):
        """Get the upstream branch of the given local branch."""
        branch_name = self.refname_to_branch_name(branch_name)
        branch = self._repo.branches[branch_name]
        result = None
        if branch.upstream:
            result = branch.upstream.branch_name
        return result

    def clone(self, url, path=None, bare=False):
        """Clone a respository at the given url, making a bare clone if specified."""
        parsed_url = urllib.parse.urlparse(url)
        url_path = Path(parsed_url.path).resolve()
        url_name = url_path.name
        target_path = path if path else str(Path.cwd() / url_name)

        callbacks = Git.RemoteCallbacks()
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
        branch_name = self.refname_to_branch_name(branch_name)
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

    def validate_config(self):
        """Ensure the git config is sane.  This is primarily a development debugging
        tool."""
        if not self.has_repo():
            return

        found = dict()

        def report_error(lines, message):
            for line in lines:
                print(line.rstrip())
            raise Exception(message)

        confpath = Path(f'{self._repo.path}')
        # This might be a worktree.  Make sure we have a config file and if not,
        # walk up until se wee one.
        while not os.path.exists(confpath / 'config'):
            newpath = confpath.parent
            if newpath == confpath:
                raise Exception(f'Cannot find git config file in {self._repo.path}')
            confpath = newpath

        with open(confpath / 'config') as conffile:
            lines = []
            secpath = ''
            section = None
            for line in conffile:
                lines.append(line)
                # Match a section header.
                match = re.match(r'^\[([^\s]*)( "([^"]*)")?\]$',
                                 line.strip())
                if match:
                    prefix = match.group(1)
                    suffix = match.group(3)  # Could be None
                    secpath = f'{prefix}.{suffix}' if suffix else f'{prefix}'
                    if not secpath in found:
                        found[secpath] = set()
                    section = found[secpath]
                else:
                    # Not a section header, try to match key = value.
                    match = re.match(r'^\s*([^\s=]+) = (.+)$', line.strip())
                    if match:
                        matched_key = match.group(1)
                        matched_value = match.group(2)
                        item = f'{matched_key} = {matched_value}'
                        if section is None:
                            report_error(lines,
                                         f'git config {item} not in section')

                        if item in section:
                            report_error(lines,
                                         f'git config duplicate entry {secpath}.{item}')
                        section.add(item)
