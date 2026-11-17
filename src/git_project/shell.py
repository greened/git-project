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

"""Helpers to run commands.

run_command_with_shell passes the command string to a shell, so the shell
parses it: quoting, pipes, redirection, globs and variables all work, and so
does anything else a shell would do with the text. Quote any value you put
into the string yourself.

capture_command and iter_command do not use a shell. They split the string
with shlex.split and run the result directly.

"""

import io
import os
import shlex
import signal
import subprocess
import tempfile
import threading


def run_command_with_shell(command, dry_run=False, show_command=False):
    """Run a command through the shell and return its exit status.

    command: The command to run, as one string for the shell to parse.

    dry_run: Print the command and do not run it. Return 0.

    show_command: Print the command before running it.

    While the command runs, SIGINT and SIGTERM do not stop this process.
    A SIGTERM is sent on to the command. A SIGINT is sent on only when
    this process is not in the terminal's foreground group, since a
    Ctrl-C there reaches the command directly. The command decides
    whether to exit, and its status is returned. Off the main thread,
    signals are left alone.

    """

    if dry_run or show_command:
        print(command)

    if not dry_run:
        if threading.current_thread() is not threading.main_thread():
            # Only the main thread can install a signal handler.
            return subprocess.Popen(command, shell=True).wait()

        proc = None
        pending = []

        def forward(signum, frame):
            if proc is None:
                pending.append(signum)
            elif not (signum == signal.SIGINT and _terminal_signals_us()):
                proc.send_signal(signum)

        # A Python handler, not SIG_IGN, so that exec resets it to the
        # default in the child.
        old_int = signal.signal(signal.SIGINT, forward)
        old_term = signal.signal(signal.SIGTERM, forward)
        try:
            proc = subprocess.Popen(command, shell=True)
            # Popen has returned, so the handler can send directly. A signal
            # queued while Popen ran is sent now, which can repeat a Ctrl-C the
            # child already got if it came after the fork.
            for signum in pending:
                proc.send_signal(signum)
            return proc.wait()
        finally:
            signal.signal(signal.SIGINT, old_int)
            signal.signal(signal.SIGTERM, old_term)

    return 0


def _terminal_signals_us():
    """Return whether our process group is in the foreground of the
    controlling terminal. A Ctrl-C there has reached the child already.

    """
    try:
        fd = os.open("/dev/tty", os.O_RDONLY)
    except OSError:
        return False
    try:
        return os.tcgetpgrp(fd) == os.getpgrp()
    except OSError:
        return False
    finally:
        os.close(fd)


def capture_command(
    command, clargs=None, dry_run=False, show_output=False, show_error=True
):
    """Run a command and return its standard output as bytes. Raise an Exception
    that holds the output and the standard error when it exits with a non-zero
    status. With dry_run, print the command and return None.

    command: The command to run, as a list of arguments or as a string that is
    split with shlex.split. No shell runs it.

    clargs: An argparse-style command-line namespace. When given, its dry_run
    attribute can turn on a dry run, show_commands prints the command before
    running it, and show_command_output can turn on show_output.

    dry_run: Whether to just print the command.

    show_output: Whether to display the command output as well as return it.

    show_error: Whether to show any standard error output.

    """
    cmd_args = command
    if not isinstance(command, str):
        command = shlex.join(command)

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

        if isinstance(cmd_args, str):
            cmd_args = shlex.split(cmd_args)

        proc = subprocess.Popen(
            cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Wait for it to finish.
        out, err = proc.communicate()

        rc = proc.poll()

        if rc != 0:
            if show_error:
                print(err, end="", flush=True)
            raise Exception(
                f"{command}: Process exited with code {rc}\nSTDOUT: {out}\nSTDERR: {err}"
            )

        if show_output:
            print(out.decode(), end="", flush=True)

        return out


def iter_command(command, clargs=None):
    """A generator that runs a command and yields its output line by line, as text.
    When the command exits with a non-zero status, raise an Exception that
    holds the status and the standard error.

    command: The command to run. It is split with shlex.split, with no shell.

    clargs: An argparse-style command-line namespace. When given, its
    show_commands prints the command first.

    """
    show_commands = False
    if clargs:
        show_commands = clargs.show_commands

    if show_commands:
        print(command)

    cmd_args = shlex.split(command)

    # Stderr goes to a file rather than a pipe. A pipe nobody reads until the
    # end fills up, and the command then blocks before it closes stdout.
    with tempfile.TemporaryFile() as errfile:
        proc = subprocess.Popen(
            cmd_args, stdout=subprocess.PIPE, stderr=errfile
        )
        yield from io.TextIOWrapper(proc.stdout)

        # Wait, because poll() returns None until the process is reaped.
        rc = proc.wait()

        if rc != 0:
            errfile.seek(0)
            err = errfile.read().decode(errors="replace")
            raise Exception(
                f"{command}: Process exited with code {rc}\nSTDERR: {err}"
            )
