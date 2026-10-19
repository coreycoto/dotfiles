"""Run each real-terminal test in a fresh, bounded Unix worker."""

import faulthandler
import functools
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


def owned_processes(root_pid):
    """Include PTY children even though they start separate process groups."""
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat="],
        capture_output=True, text=True, check=True, timeout=2,
    )
    rows = {int(pid): (int(parent), int(group), state)
            for pid, parent, group, state in
            (line.split() for line in result.stdout.splitlines())}
    owned = {root_pid}
    while True:
        children = {pid for pid, (parent, _, _) in rows.items() if parent in owned}
        if children <= owned:
            return {pid: rows[pid] for pid in owned if pid in rows}
        owned.update(children)


def run_isolated(command, *, cwd=None, env=None, timeout=30, diagnostic_grace=1):
    # A file avoids waiting for EOF on a pipe inherited by a stuck PTY child.
    with tempfile.TemporaryFile(mode="w+") as output:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        diagnostics = []
        try:
            status = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            diagnostics.append(f"Terminal worker exceeded {timeout:g}s (pid {process.pid}).")
            owned = {}
            try:
                owned.update(owned_processes(process.pid))
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                diagnostics.append(f"Process snapshot unavailable: {error}")
            try:
                # Signal-based dumps add no watchdog thread before pty.fork().
                os.kill(process.pid, signal.SIGUSR1)
                process.wait(timeout=diagnostic_grace)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
            try:
                owned.update(owned_processes(process.pid))
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                diagnostics.append(f"Final process snapshot unavailable: {error}")
            diagnostics.append("Owned processes: PID PPID PGID STATE")
            diagnostics.extend(f"{pid} {parent} {group} {state}"
                               for pid, (parent, group, state) in sorted(owned.items()))
            groups = {process.pid, *(group for _, group, _ in owned.values())}
            for group in sorted(groups, reverse=True):
                if group <= 1 or group == os.getpgrp():
                    continue
                try:
                    os.killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                diagnostics.append("Worker did not exit after SIGKILL.")
            status = 124
        output.seek(0)
        transcript = output.read()
    if diagnostics:
        transcript += "\n" + "\n".join(diagnostics) + "\n"
    return subprocess.CompletedProcess(command, status, stdout=transcript)


def isolated_terminal_test(method):
    @functools.wraps(method)
    def run(self):
        if os.environ.get("DOTFILES_TERMINAL_WORKER") == self.id():
            return method(self)
        started = time.monotonic()
        result = run_isolated(
            [sys.executable, str(Path(__file__).resolve()), self.id()],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        sys.stderr.write(f"[terminal worker {time.monotonic() - started:.2f}s] ")
    return run


if __name__ == "__main__":
    test_id = sys.argv[1]
    faulthandler.enable()
    faulthandler.register(signal.SIGUSR1, all_threads=True)
    os.environ["DOTFILES_TERMINAL_WORKER"] = test_id
    unittest.main(module=None, argv=[sys.argv[0], "-v", test_id])
