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
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License along
# with git-project. If not, see <https://www.gnu.org/licenses/>.

import argparse
import json
import sys
from typing import Any, ClassVar

from .exception import GitProjectError


class ParserManager:
    """A manager for argument parsers to track registered parsers and subparsers.
    This makes it easier to plugins to add their commands and options to various
    places in the argument parsing hierarchy.

    """

    class Parser:
        """A wrapper for an argparse parser that tracks any subparsers added to
        it."""

        class Subparser:
            """A wrapper for an argparse subparser that tracks any parsers added to it."""

            def __init__(self, key, parent, subparser):
                """Subparser constructor.

                key: The name of this Subparser

                subparser: The underlying argparse subparser.

                """
                self.key = key
                self.parent_parser = parent
                self.subparser = subparser
                self.parsers = []

            def _add_parser(self, parser):
                """Add a Parser as a child of this subparser.

                parser: The Parser to add.

                """
                self.parsers.append(parser)

            def _find_parser(self, key):
                """Given a parser key, find a matching parser under this subparser.  Recurse
                into any nested subparsers.

                key: Parser name.

                """
                for parser in self.parsers:
                    found = parser._find_parser(key)
                    if found:
                        return found
                return None

            def _find_subparser(self, key):
                """Given a subparser key, find a matching subparser under this subparser.
                Recurse into any nested parsers.

                key: Subparser name.

                """
                if self.key == key:
                    return self
                for parser in self.parsers:
                    found = parser._find_subparser(key)
                    if found:
                        return found
                return None

        class Argument:
            def __init__(
                self,
                name,
                aliases,
                has_value,
                desc,
                nargs=None,
                choices=None,
                complete=None,
                candidates=None,
                repeatable=False,
                parser=None,
            ):
                self.name = name
                self.aliases = aliases
                self.has_value = has_value
                self.description = desc
                self.nargs = nargs
                self.choices = choices
                self.complete = complete
                self.candidates = candidates
                self.repeatable = repeatable
                # The child Parser of a command.
                self.parser = parser

            def menu_nargs(self):
                return None if self.nargs is None else str(self.nargs)

            def menu_choices(self):
                if self.choices is None:
                    return None
                return list(map(str, self.choices))

            def menu_candidates(self):
                if self.candidates is None:
                    return None
                return list(map(str, self.candidates))

            def menu_names(self):
                # Keys on the long flag regardless of declaration order.
                names = [self.name, *self.aliases]
                long = next((n for n in names if n.startswith("--")), None)
                if long is None:
                    return self.name, list(self.aliases)
                return long, [n for n in names if n != long]

        def __init__(self, key, parser):
            """Parser constructor.

            key: The parser name.

            parser: The underlying argparse parser.

            """
            self.key = key
            self.parser = parser
            self.subparsers = []
            self.positional_arguments = []
            self.optional_arguments = []
            self.command_arguments = []

            # Add an option to dump machine-readable option information.
            action_class = type(
                key + "Action", (argparse.Action,), {"parser": self}
            )

            def construct(self, option_strings, dest, nargs=None, **kwargs):
                super(action_class, self).__init__(
                    option_strings, dest, nargs=nargs, **kwargs
                )

            def call(self, parser, namespace, values, option_string=None):
                parser = self.parser
                if values in ("json", "json-tree"):
                    menu = parser._menu_object(tree=values == "json-tree")
                    print(json.dumps(menu))
                    sys.exit(0)

                print("COMMANDS:")
                for command in parser.command_arguments:
                    print(f"{command.name}:{command.description}")

                print("POSITIONALS:")
                for positional in parser.positional_arguments:
                    print(f"{positional.name}:{positional.description}")

                print("OPTIONALS:")
                for optional in parser.optional_arguments:
                    print(
                        f"{optional.name}:"
                        f'{" ".join(optional.aliases)}:'
                        f"{optional.has_value}:"
                        f"{optional.description}"
                    )
                sys.exit(0)

            action_class.__init__ = construct
            action_class.__call__ = call

            parser.add_argument(
                "--menu",
                nargs="?",
                const="text",
                choices=["text", "json", "json-tree"],
                action=action_class,
                help=(
                    "Print the menu for tools, as text (the default), JSON "
                    "or JSON with every subcommand's menu nested"
                ),
            )

        def _menu_object(self, tree):
            """Return this parser's --menu=json object. With tree, each
            command also carries its child parser's object under "menu".

            """

            def command_object(command):
                obj = {
                    "name": command.name,
                    "aliases": list(command.aliases),
                    "description": command.description,
                }
                if tree:
                    obj["menu"] = command.parser._menu_object(tree)
                return obj

            def hints(argument):
                return {
                    "complete": argument.complete,
                    "candidates": argument.menu_candidates(),
                    "repeatable": argument.repeatable,
                }

            return {
                "version": 1,
                "commands": [
                    command_object(command)
                    for command in self.command_arguments
                ],
                "positionals": [
                    {
                        "name": positional.name,
                        "nargs": positional.menu_nargs(),
                        "choices": positional.menu_choices(),
                        **hints(positional),
                        "description": positional.description,
                    }
                    for positional in self.positional_arguments
                ],
                "optionals": [
                    {
                        "name": optional.menu_names()[0],
                        "aliases": optional.menu_names()[1],
                        "has_value": optional.has_value,
                        "nargs": optional.menu_nargs(),
                        "choices": optional.menu_choices(),
                        **hints(optional),
                        "description": optional.description,
                    }
                    for optional in self.optional_arguments
                ],
            }

        def _add_subparser(self, subparser):
            """Add a subparser as a child of this parser.

            subparser: Subparser to add.

            """
            self.subparsers.append(subparser)

        def _find_subparser(self, key):
            """Given a subparser key, find a matching subparser under this parser.
            Recurse into any nested parsers.

            key: Subparser name.

            """
            for subparser in self.subparsers:
                if subparser.key == key:
                    return subparser
                for parser in subparser.parsers:
                    found = parser._find_subparser(key)
                    if found:
                        return found
            return None

        def _find_parser(self, key):
            """Given a parser key, find a matching parser under this parser.  Recurse into
            any nested subparsers.

            key: Parser name.

            """
            if self.key == key:
                return self
            for subparser in self.subparsers:
                found = subparser._find_parser(key)
                if found:
                    return found
            return None

        def add_argument(self, name, *args, **kwargs):
            """Add an argument for the wrapped parser.  Accepts the same arguments as
            argparse parsers.

            args: Pass-through to the underlying argparser parser.

            kwargs: Pass-through to the underlying argparser parser, except
            for two keywords that only the JSON menus read.

            complete: What kind of value the argument takes, for a tool's
            completion: "branch", "committish", "directory", "file",
            "remote" or "worktree".

            candidates: Values to suggest. Unlike choices, argparse does not
            enforce them.

            """
            complete = kwargs.pop("complete", None)
            candidates = kwargs.pop("candidates", None)

            action = self.parser.add_argument(name, *args, **kwargs)

            # Each use of these actions adds to the value. argparse resolves
            # an action string to its class, and extend subclasses append.
            repeatable = isinstance(
                action,
                (
                    argparse._AppendAction,
                    argparse._AppendConstAction,
                    argparse._CountAction,
                ),
            )

            if name[0] in self.parser.prefix_chars:
                # argparse resolves an action by string or class. Actions
                # taking no value set nargs to 0.
                self.optional_arguments.append(
                    ParserManager.Parser.Argument(
                        name,
                        aliases=args,
                        has_value=action.nargs != 0,
                        desc=kwargs.get("help", ""),
                        nargs=kwargs.get("nargs"),
                        choices=kwargs.get("choices"),
                        complete=complete,
                        candidates=candidates,
                        repeatable=repeatable,
                    )
                )
            else:
                self.positional_arguments.append(
                    ParserManager.Parser.Argument(
                        name,
                        aliases=args,
                        has_value="nargs" in kwargs,
                        desc=kwargs.get("help", ""),
                        nargs=kwargs.get("nargs"),
                        choices=kwargs.get("choices"),
                        complete=complete,
                        candidates=candidates,
                        repeatable=repeatable,
                    )
                )

        def set_defaults(self, **kwargs):
            """Set defaults for the wrapped parser.  Accepts the same arguments as argparse
            parsers.

            kwargs: Pass-through to the underlying argparser parser.

            """
            self.parser.set_defaults(**kwargs)

        def get_default(self, name):
            """Get default for the wrapped parser.  Accepts the same arguments as argparse
            parsers.

            name: Name of the default.

            """
            return self.parser.get_default(name)

    _shared_state: ClassVar[dict[str, Any]] = {}

    def __init__(self, gitproject, project):
        """ParserManager constructor.

        gitproject: A GitProject instance.

        project: The currently active Project.

        """
        self.__dict__ = ParserManager._shared_state
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        self.main_parser = self.Parser("__main__", parser)
        self.registered_subparsers = set()
        self.registered_parsers = {"__main__"}

    def add_subparser(self, parser, key, **kwargs):
        """Add a subparser under the given parser.  Register the subparser so that the
        manager knows about it.  Raise an exception if a subparser with the
        given key already exists somewhere in the hierarchy.

        parser: The Parser under which to add the subparser.

        key: The subparser name.

        kwargs: Passthrough to argparser subparser.

        """
        if key in self.registered_subparsers:
            raise GitProjectError(f"Subparser key conflict: {key}")
        self.registered_subparsers.add(key)
        subparser = parser.Subparser(
            key, parser, parser.parser.add_subparsers(**kwargs)
        )
        parser._add_subparser(subparser)
        return subparser

    def get_or_add_subparser(self, parser, key, **kwargs):
        """Get an existing subparser under the given parser or create one if none exists.

        parser: The Parser under which to get/add the subparser.

        key: The subparser name.

        kwargs: Passthrough to argparser subparser.

        """

        subparser = self.find_subparser(key)
        if not subparser:
            subparser = self.add_subparser(parser, key, **kwargs)

        return subparser

    def add_parser(self, subparser, name, key, **kwargs):
        """Add a parser under the given subparser.  Register the parser so that the
        manager knows about it.  Raise an exception if a parser with the given
        key already exists somewhere in the hierarchy.


        subparser: The Subparser under which ti add the parser.

        name: The parser command name.

        key: The parser name.

        kwargs: Passthrough to argparse parser.

        """
        if key in self.registered_parsers:
            raise GitProjectError(f"Parser key conflict: {key}")
        self.registered_parsers.add(key)
        parser = self.Parser(
            key, subparser.subparser.add_parser(name, **kwargs)
        )

        # Note that we're adding a command argument to the parent parser.
        subparser.parent_parser.command_arguments.append(
            ParserManager.Parser.Argument(
                name,
                aliases=list(kwargs.get("aliases", [])),
                has_value=False,
                desc=kwargs.get("help", ""),
                parser=parser,
            )
        )

        subparser._add_parser(parser)
        return parser

    def get_or_add_parser(self, subparser, name, key, **kwargs):
        """Get an existing parser under the given subparser or create one if none exists.

        subparser: The Subparser under which to get/add the ubparser.

        name: The user-visible name.

        key: The subparser key.

        kwargs: Passthrough to argparse parser.

        """

        parser = self.find_parser(key)
        if not parser:
            parser = self.add_parser(subparser, name, key, **kwargs)

        return parser

    def find_subparser(self, key):
        """Return the subparser with the given key or None if no such subparser
        exists.

        key: The subparser name.

        """
        return self.main_parser._find_subparser(key)

    def find_parser(self, key):
        """Return the parser with the given key or None if no such parser exists.

        key: The parser name.

        """
        if key == "__main__":
            return self.main_parser
        return self.main_parser._find_parser(key)

    def parse_args(self, args):
        """Parse command line arguments and invoke command functions.

        args: List of argument strings.

        """
        return self.main_parser.parser.parse_args(args)

    def error(self):
        """Display a usage message to stderr."""
        self.main_parser.parser.print_usage(sys.stderr)
