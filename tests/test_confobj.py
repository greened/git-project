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

class MyThing(git_project.ConfigObject):
    def __init__(self,
                 git,
                 project_section,
                 subsection,
                 ident,
                 configitems,
                 **kwargs):
        super().__init__(git,
                         project_section,
                         subsection,
                         ident,
                         configitems,
                         **kwargs)

    @classmethod
    def get(cls, git, project_section, ident, **kwargs):
        configitems = [git_project.ConfigObjectItem('first',
                                                    'firstdefault',
                                                    'First thing'),
                       git_project.ConfigObjectItem('second',
                                                    'seconddefault',
                                                    'Second thing')]
        return super().get(git,
                           project_section,
                           'mything',
                           ident,
                           configitems,
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

def test_get(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    assert thing.first == 'firstdefault'
    assert thing.second == 'seconddefault'

def test_get_with_kwargs(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test', first='newfirst')

    assert thing.first == 'newfirst'
    assert thing.second == 'seconddefault'

def test_get_user_attribute(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    assert thing.first == 'firstdefault'
    assert thing.second == 'seconddefault'
    assert not hasattr(thing, 'third')

    thing.third = "thirddefault"

    newthing = MyThing.get(git, 'project', 'test')

    assert newthing.first == 'firstdefault'
    assert newthing.second == 'seconddefault'
    assert newthing.third == 'thirddefault'

    newthing.third = "newthird"

    anotherthing = MyThing.get(git, 'project', 'test')

    assert anotherthing.first == 'firstdefault'
    assert anotherthing.second == 'seconddefault'
    assert anotherthing.third == 'newthird'

    del newthing.third

def test_del_user_attribute(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    assert thing.first == 'firstdefault'
    assert thing.second == 'seconddefault'
    assert not hasattr(thing, 'third')

    thing.third = "thirddefault"

    newthing = MyThing.get(git, 'project', 'test')

    assert newthing.first == 'firstdefault'
    assert newthing.second == 'seconddefault'
    assert newthing.third == 'thirddefault'

    del newthing.third

    oldthing = MyThing.get(git, 'project', 'test')

    assert oldthing.first == 'firstdefault'
    assert oldthing.second == 'seconddefault'
    assert not hasattr(oldthing, 'third')

def test_multival(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.add_item('test', 'one')
    thing.add_item('test', 'two')

    values = {value for value in thing.iter_multival('test')}
    assert values == {'one', 'two'}

def test_write(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    config = thing._git.config

    assert config.get_item(thing._section, 'first') == 'firstdefault'
    assert config.get_item(thing._section, 'second') == 'seconddefault'

    assert check_lines(thing._section, 'first', 'firstdefault')
    assert check_lines(thing._section, 'second', 'seconddefault')

def test_rm(reset_directory, git):
    thing = MyThing.get(git, 'project', 'test')

    thing.rm()

    assert check_lines(thing._section, 'first', 'firstdefault',
                       section_present=False, key_present=False)
    assert check_lines(thing._section, 'second', 'seconddefault',
                       section_present=False, key_present=False)
