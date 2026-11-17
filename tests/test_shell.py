#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2020-present David A. Greene <dag@obbligato.org>

# SPDX-License-Identifier: AGPL-3.0-or-later

# Copyright 2020 David A. Greene

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

import os
import pty
import select
import shlex
import signal
import subprocess
import sys
import threading
import time

import pytest

import git_project

TIMEOUT = 10

# Counts the named signal, then exits 7 a little after the first one so that
# a duplicate delivery is counted too. With "die" it takes the default action.
CHILD = """
import signal, sys, time
hits = []
if sys.argv[1] == "die":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
else:
    signal.signal(getattr(signal, sys.argv[1]), lambda s, f: hits.append(s))
print("ready", flush=True)
deadline = time.monotonic() + 10
while not hits and time.monotonic() < deadline:
    time.sleep(0.01)
time.sleep(0.3)
print(f"got {len(hits)}", flush=True)
sys.exit(7)
"""

PARENT = """
import signal, sys
import git_project
rc = git_project.run_command_with_shell(sys.argv[1])
print(f"rc {rc}", flush=True)
restored = (
    signal.getsignal(signal.SIGINT) is signal.default_int_handler
    and signal.getsignal(signal.SIGTERM) == signal.SIG_DFL
)
print(f"restored {restored}", flush=True)
"""


def child_command(mode):
    return shlex.join([sys.executable, "-c", CHILD, mode])


def read_until(fd, marker):
    out = b""
    deadline = time.monotonic() + TIMEOUT
    while marker not in out:
        ready, _, _ = select.select([fd], [], [], deadline - time.monotonic())
        assert ready, f"timed out waiting for {marker!r}: {out!r}"
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    return out


def run_parent_and_signal(mode, signum):
    """Run PARENT without a terminal and send signum to its pid alone."""
    proc = subprocess.Popen(
        [sys.executable, "-c", PARENT, child_command(mode)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        read_until(proc.stdout.fileno(), b"ready")
        os.kill(proc.pid, signum)
        out, err = proc.communicate(timeout=TIMEOUT)
    finally:
        proc.kill()
        proc.wait(timeout=TIMEOUT)
        proc.stdout.close()
        proc.stderr.close()
    return proc.returncode, out.decode(), err.decode()


def test_run_command_with_shell_returns_zero_on_success():
    assert git_project.run_command_with_shell("true") == 0


def test_run_command_with_shell_returns_nonzero_on_failure():
    assert git_project.run_command_with_shell("false") != 0


def test_run_command_with_shell_dry_run_returns_zero():
    assert git_project.run_command_with_shell("false", dry_run=True) == 0


def test_iter_command_yields_lines():
    assert list(git_project.iter_command('printf "a\\nb\\n"')) == [
        "a\n",
        "b\n",
    ]


def test_iter_command_failure_reports_status_and_stderr():
    with pytest.raises(Exception, match="exited with code 3") as info:
        list(git_project.iter_command('sh -c "echo oops >&2; exit 3"'))
    assert "oops" in str(info.value)


def test_capture_command_takes_a_list():
    assert git_project.capture_command(["printf", "%s", "a b"]) == b"a b"


@pytest.mark.parametrize("signame", ["SIGINT", "SIGTERM"])
def test_run_command_with_shell_forwards_a_signal_sent_to_its_pid(signame):
    rc, out, err = run_parent_and_signal(signame, getattr(signal, signame))
    assert "Traceback" not in err
    assert rc == 0
    assert "got 1" in out
    assert "rc 7" in out
    assert "restored True" in out


def test_run_command_with_shell_returns_status_of_a_killed_child():
    rc, out, err = run_parent_and_signal("die", signal.SIGINT)
    assert "Traceback" not in err
    assert rc == 0
    assert f"rc {-signal.SIGINT}" in out
    assert "restored True" in out


def test_run_command_with_shell_survives_ctrl_c_from_the_terminal():
    pid, master = pty.fork()
    if pid == 0:
        try:
            os.execv(
                sys.executable,
                [sys.executable, "-c", PARENT, child_command("SIGINT")],
            )
        finally:
            os._exit(127)
    done = 0
    try:
        out = read_until(master, b"ready")
        os.write(master, b"\x03")
        out += read_until(master, b"restored")
        out += read_until(master, b"\n")
        deadline = time.monotonic() + TIMEOUT
        while True:
            done, status = os.waitpid(pid, os.WNOHANG)
            if done:
                break
            assert time.monotonic() < deadline, out
            time.sleep(0.01)
    finally:
        if not done:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(master)
    out = out.decode(errors="replace")
    assert "Traceback" not in out
    assert os.waitstatus_to_exitcode(status) == 0
    # The child shares the terminal's foreground group, so the parent must
    # not send it a second SIGINT.
    assert "got 1" in out
    assert "rc 7" in out
    assert "restored True" in out


def test_run_command_with_shell_restores_signal_handlers():
    def handler(signum, frame):
        pass

    old_int = signal.signal(signal.SIGINT, handler)
    old_term = signal.signal(signal.SIGTERM, handler)
    try:
        assert git_project.run_command_with_shell("true") == 0
        assert signal.getsignal(signal.SIGINT) is handler
        assert signal.getsignal(signal.SIGTERM) is handler
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)


def test_run_command_with_shell_runs_off_the_main_thread():
    result = []
    thread = threading.Thread(
        target=lambda: result.append(
            git_project.run_command_with_shell("exit 3")
        )
    )
    thread.start()
    thread.join(timeout=TIMEOUT)
    assert result == [3]
