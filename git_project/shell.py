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

import io
import shlex
import subprocess

def run_command_with_shell(command, dry_run=False, show_command=False):
    """Run a command.

    command: The command to run.

    clargs: argparse-style command-line namespace.

    dry_run: Whether to just print actions.

    """

    if dry_run or show_command:
        print(command)

    if not dry_run:
        proc = subprocess.Popen(command, shell=True)

        # Wait for it to complete
        proc.communicate()

def capture_command(command,
                    clargs=None,
                    dry_run=False,
                    show_output=False,
                    show_error=True):
    """Run a command and capture its standard output.

    command: The command to run.

    clargs: An argparse-style command-line namespace.

    dry_run: Whether to just print the command.

    show_output: Whether to display the command output as well as return it.

    show_error: Whether to show any standard error output.

    """
    show_commands = False
    if clargs:
        if not dry_run:
            dry_run = clargs.dry_run
            show_commands = clargs.show_commands
        if not show_output:
            show_output = clargs.show_command_output

    if dry_run:
        print(command)
    else:
        if show_commands:
            print(command)

        cmd_args = shlex.split(command)

        proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        # Wait for it to finish.
        out, err = proc.communicate()

        rc = proc.poll()

        if rc != 0:
            if show_error:
                print(err, end='', flush=True)
            raise Exception('{}: Process exited with code {}\nSTDOUT: {}\nSTDERR: {}'.format(command, rc, out, err))

        if show_output:
            print(out.decode(), end='', flush=True)

        return out

def iter_command(command, clargs=None):
    """A generator that runs a command and yields its output line by line.

    command: The command to run.

    clargs: An argparse-style command-line namespace.

    """
    show_commands = False
    if clargs:
        show_commands = clargs.show_commands

    if show_commands:
        print(command)

    cmd_args = shlex.split(command)
    proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    for line in io.TextIOWrapper(proc.stdout):
        yield line

    rc = proc.poll()

    if rc != 0:
        raise Exception('{}: Process exited with code {}\nSTDOUT: {}\nSTDERR: {}'.format(command, rc, out, err))
