#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2020-present David A. Greene <dag@obbligato.org>

# SPDX-License-Identifier: AGPL-3.0-or-later

# Copyright 2026 David A. Greene

# This file is part of git-project

# git-project is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License along
# with git-project. If not, see <https://www.gnu.org/licenses/>.

def test_get_or_add_parser_name_and_key(reset_directory, parser_manager):
    command = parser_manager.find_subparser('command')

    parser = parser_manager.get_or_add_parser(command, 'visible', 'thekey')

    # The key finds it, and a second call returns the same parser.
    assert parser_manager.find_parser('thekey') is parser
    assert parser_manager.get_or_add_parser(command, 'visible', 'thekey') is parser

    # The name is what the user types.
    clargs = parser_manager.parse_args(['visible'])
    assert clargs.command == 'visible'
