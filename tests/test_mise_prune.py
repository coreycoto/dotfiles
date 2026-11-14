"""Exercise pruning without touching installed tools or the user's home."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class MisePruneTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="mise-prune-test-")
        self.addCleanup(self.scratch.cleanup)
        self.home = Path(self.scratch.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.log = self.home / "log"
        mise = self.bin / "mise"
        mise.write_text(
            "#!" + sys.executable + "\n" +
            "import json, os, sys\nfrom pathlib import Path\n"
            "Path(os.environ['TEST_LOG']).write_text(json.dumps([sys.argv[1:], os.getcwd(), "
            "os.environ.get('MISE_OFFLINE'), os.environ.get('MISE_AUTO_INSTALL')]))\n"
            "sys.exit(int(os.environ.get('TEST_EXIT', '0')))\n"
        )
        mise.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.home), "PATH": str(self.bin), "TEST_LOG": str(self.log)}

    def run_prune(self, *args, exit_code="0"):
        return subprocess.run(
            [sys.executable, str(REPO / "scripts/mise-prune.py"), *args],
            cwd=REPO, env={**self.env, "TEST_EXIT": exit_code}, capture_output=True, text=True, timeout=10,
        )

    def test_preview_is_offline_scoped_and_home_based(self):
        result = self.run_prune("vercel", "npm:neon")
        self.assertEqual(result.returncode, 0, result.stderr)
        args, cwd, offline, auto_install = json.loads(self.log.read_text())
        self.assertEqual(args, ["--cd", str(self.home), "prune", "--tools", "--dry-run", "vercel", "npm:neon"])
        self.assertEqual(Path(cwd).resolve(), self.home.resolve())
        self.assertEqual((offline, auto_install), ("1", "false"))
        self.assertIn("untracked projects", result.stdout)

    def test_apply_requires_explicit_flag_and_forwards_failure(self):
        result = self.run_prune("--apply", "npm:agent-browser", exit_code="7")
        self.assertEqual(result.returncode, 7)
        args, _, _, _ = json.loads(self.log.read_text())
        self.assertEqual(args, ["--cd", str(self.home), "--yes", "prune", "--tools", "npm:agent-browser"])

    def test_requires_tool_names_and_rejects_version_requests(self):
        for args in ((), ("vercel@65.1.0",), ("--apply",)):
            with self.subTest(args=args):
                self.assertEqual(self.run_prune(*args).returncode, 2)
                self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
