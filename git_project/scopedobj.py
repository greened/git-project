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

from .configobj import ConfigObject

class ScopedConfigObject(ConfigObject):
    """A object backed by git-config with scoping semantics.

    Scope is only relevant for reads.  Writes will write the attribute in the
    specified object only.

    The trick with this mixin is that scope searches can be invoked at any
    scoping depth but they will always start searching from the topmost scope.
    In this way the client doesn't have to know what the topmost scope is.  It
    can do a lookup in the lowest scope and the Right Thing will happen.

    """

    @staticmethod
    def _is_unscoped(name):
        unscoped_items = {'unscoped'}
        if name.startswith('_'):
            return True
        return name in unscoped_items

    def __init__(self, git, section, subsection, ident, configitems, **kwargs):
        """ScopedConfigObject construction.

        cls: The derived class being constructed.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ScopedConfigObject.

        configitems: A list of ConfigObjectItem describing members of the config
                     section.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        super().__init__(git, section, subsection, ident, configitems, **kwargs)

    def __getattribute__(self, name):
        """Check child scopes if name is a config item otherwise get the unscoped value
        of the attribute."""
        if ScopedConfigObject._is_unscoped(name):
            return super().__getattribute__(name)

        result = self._lookup_attribute(name)

        return result if result else self.unscoped(f'{name}')

    @classmethod
    def get(cls, git, project_section, subsection, ident, configitems, **kwargs):
        """Factory to construct ConfigObjects.

        cls: The derived class being constructed.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        configitems: A list of ConfigObjectItem describing members of the config
                     section.

        **kwargs: Keyword arguments of property values to set upon
          construction.

        """
        return super().get(git,
                           project_section,
                           subsection,
                           ident,
                           configitems,
                           **kwargs)

    def _lookup_attribute(self, name):
        """Walk up the child pointers to find the topmost scope that has a given config
        item.  If this is not a git-config attribute, return None.

        name: Config item to look for.

        """
        try:
            result = self.unscoped('_child')._lookup_attribute(name)
            if result:
                return result
        except AttributeError:
            pass

        for item in self._configitems:
            if name == item.key:
                return self.unscoped(name)

        return None

    def push_scope(self, obj):
        """Push a new scope for this object.  This makes 'obj' the highest scope.  If
        called on a lower scope, 'obj' will still be placed in the highest scope
        position.

        obj: Child scopee to push.  Must inherit from ScopedConfigObject.

        """
        # Find the topmost child.
        top_scope = self
        while hasattr(top_scope, '_child'):
            top_scope = top_scope.unscoped('_child')

        assert not hasattr(top_scope, '_child')
        top_scope._child = obj

    def pop_scope(self):
        """Pop the highest scope and return it."""
        # We can't just jump to the highest scope because there is no
        # backreference to its parent and we need to remove the child from the
        # parent.  So rely on stack unwinding to get to the parent.
        try:
            child = self.unscoped('_child')
            result = child.pop_scope()
            if not result:
                # Child did not have a child, child is the highest scope.
                result = self.unscoped('_child')
                del self._child
            return result
        except AttributeError:
            # No child scope
            return None

    def unscoped(self, name):
        """Access the named attribute in the current object, ignoring scoping.

        name: Name of the attribute to access.

        """
        return super().__getattribute__(name)
