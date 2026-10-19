"""Prove worker results and deadline cleanup without relying on a real hang."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from terminal_harness import run_isolated


class TerminalHarnessTests(unittest.TestCase):
    def test_success_preserves_stdout_and_stderr(self):
        result = run_isolated([sys.executable, "-c",
                               "import sys; print('stdout'); print('stderr', file=sys.stderr)"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("stdout", result.stdout)
        self.assertIn("stderr", result.stdout)

    def test_failure_retains_original_exit_status_and_diagnostics(self):
        result = run_isolated([sys.executable, "-c",
                               "import sys; print('fixture failure', flush=True); sys.exit(7)"])
        self.assertEqual(result.returncode, 7)
        self.assertIn("fixture failure", result.stdout)

    def test_timeout_reports_stack_and_cleans_up_separate_child_group(self):
        with tempfile.TemporaryDirectory() as scratch:
            pid_file = Path(scratch) / "child-pid"
            worker = '''
import faulthandler, pathlib, signal, subprocess, sys, time
faulthandler.register(signal.SIGUSR1, all_threads=True)
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
pathlib.Path(sys.argv[1]).write_text(str(child.pid))
print("terminal fixture waiting", flush=True)
time.sleep(60)
'''
            started = time.monotonic()
            result = run_isolated([sys.executable, "-c", worker, str(pid_file)],
                                  timeout=2, diagnostic_grace=0.1)
            self.assertEqual(result.returncode, 124)
            self.assertLess(time.monotonic() - started, 10)
            self.assertIn("terminal fixture waiting", result.stdout)
            self.assertIn("exceeded 2s", result.stdout)
            self.assertIn("Owned processes:", result.stdout)
            self.assertIn('File "<string>"', result.stdout)
            child_pid = int(pid_file.read_text())
            try:
                status = subprocess.run(["/bin/ps", "-p", str(child_pid), "-o", "stat="],
                                        capture_output=True, text=True, timeout=2).stdout.strip()
                self.assertTrue(not status or status.startswith("Z"), status)
            finally:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
