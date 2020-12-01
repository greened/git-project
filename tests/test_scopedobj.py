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

from git_project import ScopedConfigObject

class ChildScope(ScopedConfigObject):
    def __init__(self, git, project_section, subsection, name):
        super().__init__(git,
                         project_section,
                         subsection,
                         name,
                         name=name,
                         value='ChildScope',
                         childonly='ChildOnly')

    @classmethod
    def get(cls, git, project_section, ident, **kwargs):
        return super().get(git,
                           project_section,
                           'childscope',
                           ident,
                           **kwargs)

class ParentScope(ScopedConfigObject):
    def __init__(self, git, project_section, subsection, name):
        super().__init__(git,
                         project_section,
                         subsection,
                         name,
                         name=name,
                         value='ParentScope',
                         parentonly='ParentOnly')

    @classmethod
    def get(cls, git, project_section, ident, **kwargs):
        return super().get(git,
                           project_section,
                           'parentscope',
                           ident,
                           **kwargs)

def test_push(reset_directory, git):
    parent = ParentScope.get(git, 'project', 'parent')

    child1 = ChildScope.get(git, 'project', 'child1')
    child2 = ChildScope.get(git, 'project', 'child2')
    child3 = ChildScope.get(git, 'project', 'child3')

    parent_name = parent.unscoped('name')

    parent.push_scope(child1)

    assert  parent.unscoped('_child') is child1

    parent.push_scope(child2)

    assert  parent.unscoped('_child') is child1
    assert  child1.unscoped('_child') is child2

    child1.push_scope(child3)

    assert  parent.unscoped('_child') is child1
    assert  child1.unscoped('_child') is child2
    assert  child2.unscoped('_child') is child3

def test_pop(reset_directory, git):
    parent = ParentScope.get(git, 'project', 'parent')

    child1 = ChildScope.get(git, 'project', 'child1')
    child2 = ChildScope.get(git, 'project', 'child2')

    parent.push_scope(child1)
    parent.push_scope(child2)

    assert  parent.unscoped('_child') is child1
    assert  child1.unscoped('_child') is child2

    popped = parent.pop_scope()

    assert popped is child2
    assert parent.unscoped('_child') is child1
    assert not hasattr(super(ChildScope, child1), '_child')

    popped = parent.pop_scope()

    assert popped is child1
    assert not hasattr(super(ParentScope, parent), '_child')

def test_attr(reset_directory, git):
    parent = ParentScope.get(git, 'project', 'parent')

    child = ChildScope.get(git, 'project', 'child')

    assert parent.value == 'ParentScope'
    assert parent.parentonly == 'ParentOnly'

    parent.push_scope(child)

    assert parent.value == 'ChildScope'
    assert parent.parentonly == 'ParentOnly'
    assert parent.childonly == 'ChildOnly'

    parent.pop_scope()

    assert parent.value == 'ParentScope'
    assert parent.parentonly == 'ParentOnly'
