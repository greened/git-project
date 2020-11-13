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

from .item import ConfigObjectItem

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
                 configitems,
                 **kwargs):
        """ConfigObject construction.  This should be treated as a private method and
        all construction should occur through the get method.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        configitems: A list of ConfigObjectItem describing members of the config
                     section.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        self._git = git
        self._project_section = project_section
        self._subsection = subsection
        self._ident = ident
        self._configitems = configitems
        self._section = ConfigObject._get_full_section(self._project_section,
                                                       self._subsection,
                                                       self._ident)
        self._set_defaults(configitems)
        self._init_from_dict(configitems, kwargs)

    @classmethod
    def get(cls,
            git,
            project_section,
            subsection,
            ident,
            configitems,
            **kwargs):
        """Factory to construct ConfigObjects.

        cls: The derived class being constructed.

        git: An object to query the repository and make config changes.

        project_section: git config section of the active project.

        subsection: An arbitrarily-long subsection appended to project_section

        ident: The name of this specific ConfigObject.

        configitems: A list of ConfigObjectItem describing members of the config
                     section.

        **kwargs: Keyword arguments of property values to set upon construction.

        """
        inits = dict()

        gitsection = ConfigObject._get_full_section(project_section,
                                                    subsection,
                                                    ident)
        if git.has_repo():
            config_section = git.config.get_section(gitsection)
            if config_section:
                for item in configitems:
                    values = [value for value in config_section.iter_multival(item.key)]
                    if len(values) == 1:
                        values = values[0]
                    if values:
                        inits[item.key] = values

        for key, value in kwargs.items():
            inits[key] = value

        result = cls(git,
                     project_section,
                     subsection,
                     ident,
                     configitems,
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
        gitsection = ConfigObject._get_full_section(project_section,
                                                    subsection,
                                                    ident)

        return True if git.config.get_section(gitsection) else False

    @classmethod
    def configitems(cls):
        """Return the config items for this ConfigObject.  By default returns the
        _configitems class attribute.  Classes without a _copnfigitems attribute
        should override this method.

        cls: The ConfigObject class to query.

        """
        return cls._configitems

    @classmethod
    def add_config_item(cls, name, default, description):
        """Add a config item for this ConfigObject.  By default it modifies the
        _configitems class attribute.  Classes without a _configitems atttribute
        should override this method.

        cls: The ConfigObject class to modify.

        """
        for item in cls.configitems():
            if item.key == name:
                return
        cls._configitems.append(ConfigObjectItem(name, default, description))

    @classmethod
    def rm_config_item(cls, name, default, description):
        """Remove a config item for this ConfigObject.  By default it modifies the
        _configitems class attribute.  Classes without a _configitems atttribute
        should override this method.

        cls: The ConfigObject class to modify.

        """
        newitems = []
        for item in cls.configitems():
            if item.key == name:
                continue
            newitems.append(item)

        cls._configitems = newitems

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

    @property
    def section(self):
        """Return the full git config section for this object."""
        return self._section

    @property
    def name(self):
        """Return the identify of this object."""
        return self._ident

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
            result = [item for item in self.iter_multival(name)]
            if not result:
                return None
            if len(result) == 1:
                result = result[0]
            return result
        def fun_set(self, value):
            self.set_item(name, value)
        prop = property(fun_get, fun_set)
        setattr(cls, name, prop)

    def set_item(self, name, value):
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

    def get_item(self, name):
        """Get the value for property 'name.'"""
        return self._git.config.get_item(self._section, name)

    def add_item(self, name, value):
        """Add an item with key name set to value.  Rather than overwriting an existing
        entry, add a new one to the git config, creeating a multi-value key.

        """
        if not hasattr(self, name):
            self._add_property(name)
        self._git.config.add_item(self._section, name, value)

    def _init_from_dict(self, configitems, values):
        """Set properties of the object using the mapping in dictionary valuees.  Mapped
        valuees that are sequences create multi-value keys.

        """
        def issequence(obj):
            if isinstance(obj, str):
                return False
            return isinstance(obj, collections.abc.Sequence)

        for item in configitems:
            value = values.get(item.key, None)
            if value:
                if issequence(value):
                    for v in value:
                        self.add_item(item.key, v)
                else:
                    self.set_item(item.key, value)

    def _set_defaults(self, configitems):
        """Query the derived class for default values of properties and set them."""
        if self._git.has_repo():
            for item in configitems:
                if item.default:
                    self.set_item(item.key, item.default)

    def iter_multival(self, name):
        """Iterate over the multiple values of a multi-value git config key."""
        for value in self._git.config.iter_multival(self._section, name):
            yield value

    def __repr__(self):
        """Serialize the object as a string."""
        return str({key:value for (key, value) in
                    map(lambda item: (item.key, [value for value in self.iter_multival(item.key)]
                                      if hasattr(self, item.key) else None),
                        self._configitems)})

    def __str__(self):
        """Serialize the object as a string."""
        return str(self.__repr__())

    def rm(self):
        """Remove the entire section of this object from the git config."""
        for item in self._configitems:
            self._git.config.rm_item(self._section, item.key, '.*')
        # Removing all section entries removes the section.
        #self._git.config.rm_section(self._section)