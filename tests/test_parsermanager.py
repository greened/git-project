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
    main.add_argument("-b", "--branch", help="Short flag first")
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
                "complete": None,
                "candidates": None,
                "repeatable": False,
                "description": "The target",
            },
            {
                "name": "where",
                "nargs": "?",
                "choices": None,
                "complete": None,
                "candidates": None,
                "repeatable": False,
                "description": "Maybe a place",
            },
            {
                "name": "mode",
                "nargs": None,
                "choices": ["fast", "slow"],
                "complete": None,
                "candidates": None,
                "repeatable": False,
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
                "complete": None,
                "candidates": None,
                "repeatable": False,
                "description": "Force it",
            },
            {
                "name": "--branch",
                "aliases": ["-b"],
                "has_value": True,
                "nargs": None,
                "choices": None,
                "complete": None,
                "candidates": None,
                "repeatable": False,
                "description": "Short flag first",
            },
            {
                "name": "--pair",
                "aliases": [],
                "has_value": True,
                "nargs": "2",
                "choices": None,
                "complete": None,
                "candidates": None,
                "repeatable": False,
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
    # Shipped in version 1, so it stays.
    assert flag["nargs"] == "0"


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
        "-b:--branch:True:Short flag first\n"
        "--pair::True:Two values\n"
    )


def add_menu_tree(parser_manager):
    command = parser_manager.find_subparser("command")
    first = parser_manager.add_parser(
        command, "first", "first", aliases=["f"], help="First"
    )
    second = parser_manager.add_parser(command, "second", "second")
    # The same command name under two parents, told apart by the link.
    for parent in (first, second):
        sub = parser_manager.add_subparser(
            parent, f"{parent.key}-command", dest=f"{parent.key}_command"
        )
        child = parser_manager.add_parser(
            sub, "add", f"{parent.key}-add", help=f"{parent.key} add"
        )
        child.add_argument(f"--{parent.key}-only", help="Only here")


def test_menu_json_tree(reset_directory, parser_manager, capsys):
    add_menu_tree(parser_manager)

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu=json-tree"]))

    assert menu["version"] == 1
    first, second = menu["commands"]
    assert first["name"] == "first"
    assert first["aliases"] == ["f"]
    for parent in (first, second):
        [add] = parent["menu"]["commands"]
        assert add["description"] == f"{parent['name']} add"
        # A leaf has an empty command list, not a missing one.
        assert add["menu"]["commands"] == []
        assert [opt["name"] for opt in add["menu"]["optionals"]] == [
            f"--{parent['name']}-only"
        ]


def test_menu_json_tree_on_subcommand(reset_directory, parser_manager, capsys):
    add_menu_tree(parser_manager)

    menu = json.loads(
        run_menu(parser_manager, capsys, ["second", "--menu=json-tree"])
    )

    [add] = menu["commands"]
    assert add["description"] == "second add"
    assert add["menu"]["commands"] == []


def test_menu_json_has_no_nested_menu(reset_directory, parser_manager, capsys):
    add_menu_tree(parser_manager)

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu=json"]))

    assert all("menu" not in command for command in menu["commands"])


def add_hinted_arguments(parser_manager):
    command = parser_manager.find_subparser("command")
    main = parser_manager.add_parser(command, "hinted", "hinted")
    main.add_argument(
        "name",
        complete="worktree",
        candidates=["one", 2],
        help="A worktree",
    )
    main.add_argument("--branch", complete="branch", help="A branch")


@pytest.mark.parametrize("values", ["json", "json-tree"])
def test_menu_json_hints(reset_directory, parser_manager, capsys, values):
    add_hinted_arguments(parser_manager)

    menu = json.loads(
        run_menu(parser_manager, capsys, ["hinted", f"--menu={values}"])
    )

    [name] = menu["positionals"]
    assert name["complete"] == "worktree"
    assert name["candidates"] == ["one", "2"]
    [branch] = [opt for opt in menu["optionals"] if opt["name"] == "--branch"]
    assert branch["complete"] == "branch"
    assert branch["candidates"] is None


def test_menu_hints_are_not_argparse_arguments(
    reset_directory, parser_manager, capsys
):
    add_hinted_arguments(parser_manager)

    # candidates suggests values but does not restrict them.
    clargs = parser_manager.parse_args(["hinted", "three", "--branch", "b"])
    assert clargs.name == "three"
    assert not hasattr(clargs, "complete")
    assert not hasattr(clargs, "candidates")

    usage = run_menu(parser_manager, capsys, ["hinted", "-h"])
    assert "worktree" not in usage.replace("A worktree", "")
    assert "one" not in usage


class _CollectAction(argparse._AppendAction):
    pass


@pytest.mark.parametrize(
    ("kwargs", "repeatable"),
    [
        ({"action": "append"}, True),
        ({"action": argparse._AppendAction}, True),
        ({"action": argparse._AppendConstAction, "const": 1}, True),
        ({"action": argparse._ExtendAction, "nargs": "+"}, True),
        ({"action": argparse._CountAction}, True),
        ({"action": _CollectAction}, True),
        ({"action": "append_const", "const": 1}, True),
        ({"action": "extend", "nargs": "+"}, True),
        ({"action": "count"}, True),
        ({"action": "store_true"}, False),
        ({}, False),
    ],
)
def test_menu_json_repeatable(
    reset_directory, parser_manager, capsys, kwargs, repeatable
):
    main = parser_manager.find_parser("__main__")
    main.add_argument("--opt", help="An option", **kwargs)

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu=json"]))

    [opt] = [opt for opt in menu["optionals"] if opt["name"] == "--opt"]
    assert opt["repeatable"] is repeatable


def test_menu_json_nargs(reset_directory, parser_manager, capsys):
    main = parser_manager.find_parser("__main__")
    main.add_argument("pair", nargs=2, help="Two values")
    main.add_argument("rest", nargs=argparse.REMAINDER, help="The rest")

    menu = json.loads(run_menu(parser_manager, capsys, ["--menu=json"]))

    assert [pos["nargs"] for pos in menu["positionals"]] == ["2", "..."]


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
