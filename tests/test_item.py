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

def test_init(reset_directory):
    item = git_project.ConfigObjectItem('test', 'testdefault', 'The test')

    assert item._key == 'test'
    assert item._default == 'testdefault'
    assert item._description == 'The test'

def test_key(reset_directory):
    item = git_project.ConfigObjectItem('test', 'testdefault', 'The test')

    assert item.key == 'test'

def test_default(reset_directory):
    item = git_project.ConfigObjectItem('test', 'testdefault', 'The test')

    assert item.default == 'testdefault'

def test_description(reset_directory):
    item = git_project.ConfigObjectItem('test', 'testdefault', 'The test')

    assert item.description == 'The test'
