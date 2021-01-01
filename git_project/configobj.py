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

import collections
import inspect

class ConfigObject(object):
    """Base class for objects that use git-config as a backing store.  Specified
    property values are saved to the git config file and read from the config
    file upon instantiation.
    """
    def __init__(self,
                 git,
                 project_section,
                 subsection,
                 ident,
                 **kwargs):
        """ConfigObject construction.  This should be treated as a private method and
        all construction should occur through the get method.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        self._git = git
        self._project_section = project_section
        self._subsection = subsection
        self._ident = ident
        self._section = ConfigObject._get_full_section(self._project_section,
                                                       self._subsection,
                                                       self._ident)
        self._init_from_dict(kwargs)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
            return

        # The git config can only handle string values.
        assert(isinstance(value, str))
        self._set_item(name, value)

    def __delattr__(self, name):
        if name.startswith('_'):
            super().__delattr__(name)
            return
        self.rm_items(name)

    @classmethod
    def get(cls,
            git,
            project_section,
            subsection,
            ident,
            **kwargs):
        """Factory to construct ConfigObjects.

        cls: The derived class being constructed.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        inits = dict()

        gitsection = ConfigObject._get_full_section(project_section,
                                                    subsection,
                                                    ident)
        if git.has_repo():
            config_section = git.config.get_section(gitsection)
            if config_section:
                for key, item in config_section:
                    name = key.rsplit('.', 1)[-1]
                    if item.is_multival():
                        inits[name] = [value for value in item.itervalues()]
                    else:
                        inits[name] = item.get_value()

        for key, value in kwargs.items():
            inits[key] = value

        result = cls(git,
                     project_section,
                     subsection,
                     ident,
                     **inits)

        return result

    @classmethod
    def exists(cls,
               git,
               project_section,
               subsection,
               ident):
        """Return whether an existing git config exists for the ConfigObject.

        cls: The derived class being checked.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        """
        if not git.has_repo():
            return False

        gitsection = ConfigObject._get_full_section(project_section,
                                                    subsection,
                                                    ident)

        section = git.config.get_section(gitsection)
        return True if section else False

    @staticmethod
    def _get_full_section(section, subsection, ident):
        """Construct a full git section name by appending subsection and ident (if not
        None) to section.

        """
        result = section
        if subsection:
            result += '.' + subsection
        if ident:
            result += '.' + ident
        return result

    @classmethod
    def get_managing_command(cls):
        """Return a command-line command key that manages the ConfigObject.  Derived
        classes should override this method if they are managed by a
        command-line command.

        """
        return None

    @classmethod
    def _add_property(cls, name):
        """Add a property name that reads the git config when accessed and writes the
        git config when written."""
        def fun_get(self):
            result = {item for item in self.iter_multival(name)}
            if not result:
                return None
            if len(result) == 1:
                return result.pop()
            return frozenset(result)
        def fun_set(self, value):
            self._set_item(name, value)
        prop = property(fun_get, fun_set)
        setattr(cls, name, prop)

    def has_item(self, name):
        """Return whether self.<name> exists.  We don't want to use hasattr because
        <name> is actually set on the class, not the instance.

        """
        if not isinstance(getattr(type(self), name, None), property):
            return False

        # It's not quite enough to know we have a property.  We might have a
        # property from a previous instance but the git config entry in this
        # instance might not be set.  This should not happen during normal
        # operation as the command is quickly executed and the program
        # terminates.  However, testing can have long-lived classes with many
        # properties added to them.
        if not self._git.has_repo():
            return False

        return self._git.config.has_item(self.get_section(), name)

    def get_ident(self):
        """Return the identifier of this object."""
        return self._ident

    def get_section(self):
        """Return the section of this object."""
        return self._section

    def get_subsection(self):
        """Return the subsection of this object."""
        return self._subsection

    def _set_item(self, name, value):
        """Set property name to value and write it to the git config."""
        if not hasattr(self.__class__, name):
            self._add_property(name)
        self._git.config.set_item(self._section, name, value)

    def rm_item(self, name, pattern):
        """Remove property name values matching pattern from the git config."""
        self._git.config.rm_item(self._section, name, pattern)

    def rm_items(self, name):
        """Remove property name completely from the git config."""
        self._git.config.rm_items(self._section, name)
        delattr(self.__class__, name)

    def _get_item(self, name):
        """Get the value for property 'name.'"""
        return self._git.config.get_item(self._section, name)

    def add_item(self, name, value):
        """Add an item with key name set to value.  Rather than overwriting an existing
        entry, add a new one to the git config, creeating a multi-value key.

        """
        if not hasattr(self, name):
            self._add_property(name)
        self._git.config.add_item(self._section, name, value)

    def _init_from_dict(self, values):
        """Set properties of the object using the mapping in dictionary valuees.  Mapped
        valuees that are sequences create multi-value keys.

        """
        def issequence(obj):
            if isinstance(obj, str):
                return False
            return isinstance(obj, collections.abc.Sequence)

        for key, value in values.items():
            if issequence(value):
                for v in value:
                    self.add_item(key, v)
            else:
                self._set_item(key, value)

    def iter_multival(self, name):
        """Iterate over the multiple values of a multi-value git config key."""
        for value in self._git.config.iter_multival(self._section, name):
            yield value

    def __repr__(self):
        """Serialize the object as a string."""
        return str({key:value for (key, value) in
                    self.__dict__.items() if not key.startswith('_')})

    def __str__(self):
        """Serialize the object as a string."""
        return str(self.__repr__())

    def rm(self):
        """Remove the entire section of this object from the git config."""
        for key, value in self.iteritems():
            self.rm_items(key)
        # Removing all section entries removes the section.
        #self._git.config.rm_section(self._section)

    def iteritems(self):
        """Iterate over all key, value items."""
        for key, value in inspect.getmembers(self):
            if self.has_item(key):
                yield key, value
