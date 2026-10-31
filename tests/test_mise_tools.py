"""Exercise tool maintenance previews and ownership boundaries."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class MiseToolsTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="mise-tools-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        shutil.copyfile(REPO / "scripts/mise-tools.py", scripts / "mise-tools.py")
        self.source = self.root / "home/dot_config/mise/config.toml"
        self.source.parent.mkdir(parents=True)
        self.original = '[tools]\nnode = "24.21.0"\nvercel = { version = "latest", auto_update = "24h" }\n'
        self.source.write_text(self.original)
        self.live = self.root / ".config/mise/config.toml"
        self.live.parent.mkdir(parents=True)
        self.live.write_text(self.original)
        self.bins = self.root / "bin"
        self.bins.mkdir()
        self.log = self.root / "commands.jsonl"
        for name in ("mise", "brew"):
            fake = self.bins / name
            fake.write_text(
                "#!" + sys.executable + "\n" + r'''import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
with Path(os.environ["TEST_LOG"]).open("a") as output:
    output.write(json.dumps({"name": name, "args": sys.argv[1:], "cwd": os.getcwd(),
        "prune": os.environ.get("MISE_UPGRADE_AUTO_PRUNE"),
        "cleanup": os.environ.get("HOMEBREW_NO_INSTALL_CLEANUP"),
        "offline": os.environ.get("MISE_OFFLINE")}) + "\n")
sys.exit(int(os.environ.get("TEST_" + name.upper() + "_EXIT", "0")))
'''
            )
            fake.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.root), "XDG_CONFIG_HOME": str(self.root / ".config"),
                    "PATH": str(self.bins) + os.pathsep + "/usr/bin:/bin", "TEST_LOG": str(self.log)}

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(self.root / "scripts/mise-tools.py"), *args],
                              env=self.env, capture_output=True, text=True, timeout=10)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_install_preview_does_not_execute_or_write(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("install node vercel", result.stdout)
        self.assertFalse(self.log.exists())
        self.assertEqual(self.source.read_text(), self.original)

    def test_update_preview_queries_both_managers_without_changing_requests(self):
        result = self.run_script("--update")
        self.assertEqual(result.returncode, 0, result.stderr)
        mise, brew = self.calls()
        self.assertEqual((mise["name"], mise["args"]),
                         ("mise", ["--cd", str(self.root), "upgrade", "--global", "--dry-run", "node", "vercel"]))
        self.assertEqual((brew["name"], brew["args"]), ("brew", ["upgrade", "--dry-run"]))
        self.assertEqual(mise["prune"], "false")
        self.assertEqual(brew["cleanup"], "1")
        self.assertEqual(Path(mise["cwd"]).resolve(), self.root.resolve())
        self.assertEqual(Path(brew["cwd"]).resolve(), self.root.resolve())
        self.assertEqual(self.source.read_text(), self.original)
        self.assertEqual(self.live.read_text(), self.original)

    def test_explicit_apply_installs_only_selected_global_tools_from_home(self):
        result = self.run_script("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([(c["name"], c["args"]) for c in self.calls()],
                         [("mise", ["--cd", str(self.root), "install", "node", "vercel"])])
        self.assertEqual(self.source.read_text(), self.original)
        self.assertEqual(self.live.read_text(), self.original)

    def test_update_applies_both_without_bumping_or_cleanup(self):
        result = self.run_script("--update", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        mise, brew = self.calls()
        self.assertEqual([mise["name"], brew["name"]], ["mise", "brew"])
        self.assertEqual(mise["args"], ["--cd", str(self.root), "upgrade", "--global", "node", "vercel"])
        self.assertEqual(brew["args"], ["upgrade"])
        self.assertEqual(mise["prune"], "false")
        self.assertEqual(brew["cleanup"], "1")
        self.assertEqual(self.source.read_text(), self.original)
        self.assertEqual(self.live.read_text(), self.original)

    def test_mise_failure_stops_before_homebrew(self):
        self.env["TEST_MISE_EXIT"] = "7"
        result = self.run_script("--update", "--apply")
        self.assertEqual(result.returncode, 7)
        self.assertEqual([c["name"] for c in self.calls()], ["mise"])
        self.assertIn("Homebrew was not run", result.stderr)
        self.assertIn("partially completed", result.stderr)

    def test_brew_failure_reports_partial_completion(self):
        self.env["TEST_BREW_EXIT"] = "9"
        result = self.run_script("--update", "--apply")
        self.assertEqual(result.returncode, 9)
        self.assertEqual([c["name"] for c in self.calls()], ["mise", "brew"])
        self.assertIn("Mise upgrade completed", result.stderr)
        self.assertIn("Homebrew upgrade failed", result.stderr)
        self.assertIn("partially completed", result.stderr)

    def test_different_or_missing_live_config_stops_before_either_manager(self):
        self.live.write_text('[tools]\nnode = "22"\n')
        result = self.run_script("--update", "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())
        self.live.unlink()
        result = self.run_script("--update")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())

    def test_missing_manager_stops_before_either_manager(self):
        for manager in ("mise", "brew"):
            with self.subTest(manager=manager):
                path = self.bins / manager
                hidden = self.bins / (manager + ".hidden")
                path.rename(hidden)
                try:
                    result = self.run_script("--update", "--apply")
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(manager, result.stderr)
                    self.assertFalse(self.log.exists())
                finally:
                    hidden.rename(path)


if __name__ == "__main__":
    unittest.main()
