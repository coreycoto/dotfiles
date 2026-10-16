"""Exercise Mise maintenance previews and ownership boundaries."""

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
        bins = self.root / "bin"
        bins.mkdir()
        self.log = self.root / "commands.json"
        fake = bins / "mise"
        fake.write_text("#!" + sys.executable + '\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["TEST_LOG"]).write_text(json.dumps(sys.argv[1:]))\nsys.exit(int(os.environ.get("TEST_EXIT", "0")))\n')
        fake.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.root), "XDG_CONFIG_HOME": str(self.root / ".config"),
                    "PATH": str(bins) + os.pathsep + os.environ["PATH"], "TEST_LOG": str(self.log)}

    def run_script(self, *args):
        script = self.root / "scripts/mise-tools.py"
        return subprocess.run([sys.executable, str(script), *args], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_install_preview_does_not_execute_or_write(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("install node vercel", result.stdout)
        self.assertFalse(self.log.exists())
        self.assertEqual(self.source.read_text(), self.original)

    def test_update_preview_uses_dry_run_without_bumping_requests(self):
        result = self.run_script("--update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.log.read_text()),
                         ["--cd", str(self.root), "upgrade", "--global", "--dry-run", "node", "vercel"])
        self.assertEqual(self.source.read_text(), self.original)
        self.assertEqual(self.live.read_text(), self.original)

    def test_explicit_apply_installs_only_selected_global_tools_from_home(self):
        result = self.run_script("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.log.read_text()), ["--cd", str(self.root), "install", "node", "vercel"])
        self.assertEqual(self.source.read_text(), self.original)
        self.assertEqual(self.live.read_text(), self.original)

    def test_failed_upgrade_does_not_rewrite_requests(self):
        self.env["TEST_EXIT"] = "7"
        result = self.run_script("--update", "--apply")
        self.assertNotEqual(result.returncode, 0)
        command = json.loads(self.log.read_text())
        self.assertNotIn("--bump", command)
        self.assertNotIn("--prune", command)
        self.assertNotIn("--dry-run", command)
        self.assertEqual(self.source.read_text(), self.original)
        self.assertEqual(self.live.read_text(), self.original)

    def test_unapplied_or_different_live_config_stops_before_install(self):
        self.live.write_text('[tools]\nnode = "22"\n')
        result = self.run_script("--apply")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())
        self.live.unlink()
        result = self.run_script("--update")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
