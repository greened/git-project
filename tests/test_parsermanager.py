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

import argparse
import json

import pytest

from git_project.test_support import ParserManagerMock


def test_get_or_add_parser_name_and_key(reset_directory, parser_manager):
    command = parser_manager.find_subparser("command")

    parser = parser_manager.get_or_add_parser(command, "visible", "thekey")

    # The key finds it, and a second call returns the same parser.
    assert parser_manager.find_parser("thekey") is parser
    assert (
        parser_manager.get_or_add_parser(command, "visible", "thekey")
        is parser
    )

    # The name is what the user types.
    clargs = parser_manager.parse_args(["visible"])
    assert clargs.command == "visible"


def run_menu(parser_manager, capsys, args):
    with pytest.raises(SystemExit) as exit_info:
        parser_manager.parse_args(args)
    assert exit_info.value.code == 0
    return capsys.readouterr().out


def add_menu_entries(parser_manager):
    command = parser_manager.find_subparser("command")
    parser_manager.add_parser(
        command,
        "multirepo",
        "multirepo",
        aliases=["mr", "multi"],
        help="Run commands across repositories",
    )
    parser_manager.add_parser(command, "plain", "plain", help="No aliases")
    main = parser_manager.find_parser("__main__")
    main.add_argument("target", help="The target")
    main.add_argument("where", nargs="?", help="Maybe a place")
    main.add_argument("mode", choices=["fast", "slow"], help="A mode")
    main.add_argument("--force", "-f", action="store_true", help="Force it")
    main.add_argument("--pair", nargs=2, help="Two values")


def test_menu_json(reset_directory, parser_manager, capsys):
    add_menu_entries(parser_manager)

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu=json"]))

    assert menu == {
        "version": 1,
        "commands": [
            {
                "name": "multirepo",
                "aliases": ["mr", "multi"],
                "description": "Run commands across repositories",
            },
            {"name": "plain", "aliases": [], "description": "No aliases"},
        ],
        "positionals": [
            {
                "name": "target",
                "nargs": None,
                "choices": None,
                "description": "The target",
            },
            {
                "name": "where",
                "nargs": "?",
                "choices": None,
                "description": "Maybe a place",
            },
            {
                "name": "mode",
                "nargs": None,
                "choices": ["fast", "slow"],
                "description": "A mode",
            },
        ],
        "optionals": [
            {
                "name": "--force",
                "aliases": ["-f"],
                "has_value": False,
                "nargs": None,
                "choices": None,
                "description": "Force it",
            },
            {
                "name": "--pair",
                "aliases": [],
                "has_value": True,
                "nargs": "2",
                "choices": None,
                "description": "Two values",
            },
        ],
    }


@pytest.mark.parametrize("action", ["append", "extend"])
def test_menu_json_collecting_action_has_value(
    reset_directory, parser_manager, capsys, action
):
    main = parser_manager.find_parser("__main__")
    main.add_argument("--item", action=action, help="Collect items")

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu=json"]))

    [item] = [opt for opt in menu["optionals"] if opt["name"] == "--item"]
    assert item["has_value"] is True
    assert item["nargs"] is None


class _FlagAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, True)


def test_menu_json_custom_flag_action_has_no_value(
    reset_directory, parser_manager, capsys
):
    main = parser_manager.find_parser("__main__")
    main.add_argument("--flag", action=_FlagAction, nargs=0, help="A flag")

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu=json"]))

    [flag] = [opt for opt in menu["optionals"] if opt["name"] == "--flag"]
    assert flag["has_value"] is False


def test_menu_json_separate_value(reset_directory, parser_manager, capsys):
    add_menu_entries(parser_manager)

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu", "json"]))

    assert menu["version"] == 1
    assert menu["commands"][0]["aliases"] == ["mr", "multi"]


@pytest.mark.parametrize("args", [["--menu"], ["--menu=text"]])
def test_menu_text_unchanged(reset_directory, parser_manager, capsys, args):
    add_menu_entries(parser_manager)

    assert run_menu(parser_manager, capsys, args) == (
        "COMMANDS:\n"
        "multirepo:Run commands across repositories\n"
        "plain:No aliases\n"
        "POSITIONALS:\n"
        "target:The target\n"
        "where:Maybe a place\n"
        "mode:A mode\n"
        "OPTIONALS:\n"
        "--force:-f:False:Force it\n"
        "--pair::True:Two values\n"
    )


def test_menu_rejects_other_values(reset_directory, parser_manager):
    with pytest.raises(SystemExit) as exit_info:
        parser_manager.parse_args(["--menu", "worktree"])
    assert exit_info.value.code == 2


def test_parser_mock_equality():
    def make(help_text):
        parser = ParserManagerMock.ParserMock("thekey")
        parser.add_argument("name", help=help_text)
        parser.set_defaults(func="handler")
        return parser

    assert make("same") == make("same")
    assert make("same") != make("different")
