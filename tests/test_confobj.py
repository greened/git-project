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

import inspect
import os
import re

import git_project
from git_project.test_support import check_config_file

from pathlib import Path
import shutil

class MyThing(git_project.ConfigObject):
    def __init__(self,
                 git,
                 project_section,
                 subsection,
                 ident,
                 **kwargs):
        super().__init__(git,
                         project_section,
                         subsection,
                         ident,
                         **kwargs)

    @classmethod
    def get(cls, git, project_section, ident, **kwargs):
        return super().get(git,
                           project_section,
                           'mything',
                           ident,
                           **kwargs)

def check_lines(section,
                key,
                value,
                section_present = True,
                key_present = True):
    found = False
    prefix, suffix = section.split('.', 1)

    with open('config') as conffile:
        found_section = False
        for line in conffile:
            if not found_section:
                if line.strip() == f'[{prefix} "{suffix}"]':
                    if not section_present:
                        # This shouldn't be here
                        return False
                    found_section = True
                    if not key:
                        return True
            elif key:
                if line.strip() == f'{key} = {value}':
                    if key_present:
                        return True

        # Didn't find the section or found the section but not the key.

        if found_section:
            if not section_present:
                return False
        elif not section_present:
            return True

        if not key_present:
            return True

        return False

def test_confobj_get(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    assert not hasattr(thing, 'first')
    assert not hasattr(thing, 'second')

    git.config.set_item(thing.get_section(), 'first', 'firstdefault')
    git.config.set_item(thing.get_section(), 'second', 'seconddefault')

    thing = MyThing.get(git, 'project', 'test')

    assert thing.first == 'firstdefault'
    assert thing.second == 'seconddefault'

def test_confobj_get_with_kwargs(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test', first='newfirst')

    assert thing.first == 'newfirst'

def test_confobj_name(reset_directory, git):
    """Test that we translate illegal section names correctly."""

    thing = MyThing.get(git, '__my_problematic.project', 'test')

    assert thing.get_section() == 'ZZ--my-problematic-project.mything.test'

def test_confobj_get_user_attribute(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    assert not hasattr(thing, 'third')

    thing.third = "thirddefault"

    newthing = MyThing.get(git, 'project', 'test')

    assert newthing.third == 'thirddefault'

    newthing.third = "newthird"

    anotherthing = MyThing.get(git, 'project', 'test')

    assert anotherthing.third == 'newthird'

    del newthing.third

def test_confobj_del_user_attribute(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    assert not hasattr(thing, 'third')

    thing.third = "thirddefault"

    newthing = MyThing.get(git, 'project', 'test')

    assert newthing.third == 'thirddefault'

    del newthing.third

    oldthing = MyThing.get(git, 'project', 'test')

    assert not hasattr(oldthing, 'third')

def test_confobj_multival(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.add_item('test', 'one')
    thing.add_item('test', 'two')

    values = {value for value in thing.iter_multival('test')}
    assert values == {'one', 'two'}

def test_confobj_write(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.first = 'firstdefault'
    thing.second = 'seconddefault'

    config = thing._git.config

    assert config.get_item(thing._section, 'first') == 'firstdefault'
    assert config.get_item(thing._section, 'second') == 'seconddefault'

    assert check_lines(thing._section, 'first', 'firstdefault')
    assert check_lines(thing._section, 'second', 'seconddefault')

def test_confobj_rm(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.first = 'firstdefault'
    thing.second = 'seconddefault'

    config = thing._git.config

    assert config.get_item(thing._section, 'first') == 'firstdefault'
    assert config.get_item(thing._section, 'second') == 'seconddefault'

    assert check_lines(thing._section, 'first', 'firstdefault')
    assert check_lines(thing._section, 'second', 'seconddefault')

    thing.rm()

    assert check_lines(thing._section, 'first', 'firstdefault',
                       section_present=False, key_present=False)
    assert check_lines(thing._section, 'second', 'seconddefault',
                       section_present=False, key_present=False)

def test_confobj_iteritems(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.first = 'firstdefault'
    thing.second = 'seconddefault'

    result = [(key, value) for key, value in thing.iteritems()]

    assert result == [('first', 'firstdefault'), ('second', 'seconddefault')]

def test_confobj_iteritems_multi(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.first = 'firstdefault'
    thing.second = 'seconddefault'

    thing.add_item('second', 'secondsecond')

    result = [(key, value) for key, value in thing.iteritems()]

    assert result == [('first', 'firstdefault'),
                      ('second', {'seconddefault', 'secondsecond'})]

def test_confobj_get_multi(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.first = 'firstdefault'
    thing.second = 'seconddefault'

    thing.add_item('second', 'secondsecond')

    newthing  = MyThing.get(git, 'project', 'test')

    result = [(key, value) for key, value in thing.iteritems()]

    assert result == [('first', 'firstdefault'),
                      ('second', {'seconddefault', 'secondsecond'})]

def test_confobj_get_no_dup(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.first = 'firstdefault'
    thing.second = 'seconddefault'

    thing.add_item('second', 'secondsecond')
    thing.add_item('second', 'secondthird')

    newthing  = MyThing.get(git, 'project', 'test')

    check_config_file('project.mything.test', 'first', {'firstdefault'})

    check_config_file('project.mything.test',
                      'second',
                      {'seconddefault', 'secondsecond', 'secondthird'})

    os.chdir(git._repo.path)

    newgit = git_project.Git()

    check_config_file('project.mything.test', 'first', {'firstdefault'})

    check_config_file('project.mything.test',
                      'second',
                      {'seconddefault', 'secondsecond', 'secondthird'})
