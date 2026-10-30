"""Exercise command routing without changing the user's tools or home."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class DotfilesCliTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="dotfiles-cli-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        scripts = self.root / "checkout/scripts"
        scripts.mkdir(parents=True)
        self.cli = scripts / "dotfiles.py"
        shutil.copyfile(REPO / "scripts/dotfiles.py", self.cli)
        (scripts / "mise-tools.py").write_text(
            'import json, os, sys\nfrom pathlib import Path\n'
            'Path(os.environ["TEST_LOG"]).write_text(json.dumps(sys.argv[1:]))\n'
            'sys.exit(int(os.environ.get("TEST_EXIT", "0")))\n'
        )
        check = scripts / "check"
        check.write_text('#!/bin/sh\npwd > "$TEST_LOG"\nexit "${TEST_EXIT:-0}"\n')
        check.chmod(0o755)
        self.log = self.root / "log"
        self.env = {**os.environ, "TEST_LOG": str(self.log)}

    def run_cli(self, *args, exit_code="0"):
        return subprocess.run(
            [sys.executable, str(self.cli), *args], cwd=self.root,
            env={**self.env, "TEST_EXIT": exit_code}, capture_output=True, text=True, timeout=10,
        )

    def test_help_and_invalid_arguments_do_not_run_commands(self):
        for args in ((), ("--help",)):
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            for command in ("install", "update", "check"):
                self.assertIn(command, result.stdout)
        for args in (("unknown",), ("check", "--dry-run"), ("update", "--apply")):
            self.assertEqual(self.run_cli(*args).returncode, 2)
        self.assertFalse(self.log.exists())

    def test_tool_commands_forward_the_expected_flags_and_exit_status(self):
        for args, expected in (
            (("install",), ["--apply"]),
            (("install", "--dry-run"), []),
            (("update",), ["--update", "--apply"]),
            (("update", "--dry-run"), ["--update"]),
        ):
            with self.subTest(args=args):
                result = self.run_cli(*args, exit_code="7")
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertEqual(json.loads(self.log.read_text()), expected)

    def test_check_runs_from_checkout_and_forwards_failure(self):
        result = self.run_cli("check", exit_code="9")
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertEqual(Path(self.log.read_text().strip()).resolve(), (self.root / "checkout").resolve())


if __name__ == "__main__":
    unittest.main()
