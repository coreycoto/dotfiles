"""Qualify durable runtime acquisition and path-only launchd repair without host changes."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portless_service", REPO / "scripts/portless-service.py")
service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(service)


class PortlessServiceTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="dotfiles-portless-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.version, self.node_version = service.selection()
        self.runtime = self.home / ".local/share/portless" / self.version
        self.source = self.root / "live.plist"
        self.spec = {
            "Label": "sh.portless.proxy",
            "ProgramArguments": ["/old/Cellar/node/bin/node", "/project/node_modules/.bin/portless",
                                 "proxy", "start", "--foreground", "--https", "--port", "443", "--skip-trust"],
            "EnvironmentVariables": {"HOME": str(self.home), "PORTLESS_STATE_DIR": str(self.home / ".portless"),
                                     "SUDO_UID": "501", "SUDO_GID": "20", "PORTLESS_LAN": "0"},
            "RunAtLoad": True, "KeepAlive": True, "StandardOutPath": str(self.home / ".portless/service.log"),
        }
        self.source.write_bytes(plistlib.dumps(self.spec))
        source_repo = self.root / "source"
        for name in ("tools/portless/package.json", "tools/portless/bun.lock", "home/dot_config/mise/config.toml"):
            target = source_repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, target)
        sample = self.root / "sample"
        self.package(sample)
        inventory = {str(p.relative_to(sample)): {"bytes": p.stat().st_size,
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sample.rglob("*") if p.is_file()}
        (source_repo / "tools/portless/runtime.json").write_text(json.dumps({"version": self.version, "files": inventory}))
        patcher = patch.object(service, "REPO", source_repo)
        patcher.start()
        self.addCleanup(patcher.stop)

    def package(self, path):
        (path / "dist").mkdir(parents=True)
        (path / "package.json").write_text(json.dumps({"name": "portless", "version": self.version}))
        (path / "dist/cli.js").write_text("// synthetic package fixture\n")
        (path / "README.md").write_text("synthetic fixture\n")

    def download(self, args, *, cwd, check):
        self.assertEqual(args, ["/reviewed/bun", "install", "--frozen-lockfile", "--ignore-scripts"])
        self.assertTrue(check)
        self.assertEqual((cwd / "bun.lock").read_bytes(), (REPO / "tools/portless/bun.lock").read_bytes())
        self.package(cwd / "node_modules/portless")

    def versions(self, args, **kwargs):
        self.assertEqual(args[0], str(self.home / ".local/share/mise/installs/node" / self.node_version.split(".")[0] / "bin/node"))
        return subprocess.CompletedProcess(args, 0, "v" + self.node_version if len(args) == 2 else self.version, "")

    def test_locked_install_is_repeatable_and_does_not_replace_existing_bytes(self):
        with patch.object(service.subprocess, "run", side_effect=self.download):
            self.assertEqual(service.install_runtime(self.home, "/reviewed/bun"), self.runtime)
            before = service.runtime_tree(self.runtime)
            self.assertEqual(service.install_runtime(self.home, "/reviewed/bun"), self.runtime)
            self.assertEqual(service.runtime_tree(self.runtime), before)
            (self.runtime / "README.md").write_text("unowned local change")
            with self.assertRaisesRegex(ValueError, "Runtime package bytes differ"):
                service.install_runtime(self.home, "/reviewed/bun")
        self.assertEqual((self.runtime / "README.md").read_text(), "unowned local change")
        self.assertEqual(list(self.runtime.parent.glob(".install-*")), [])

    def test_approved_repair_marker_is_preserved_but_tampering_and_extras_fail(self):
        self.package(self.runtime)
        entries = [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                    "mode": (self.runtime / name).stat().st_mode & 0o777}
                   for name, data in service.runtime_tree(self.runtime).items()]
        receipt = {"version": 1, "repository": "coreycoto/atelier", "task": 148,
                   "purpose": "portless-service-repair-proposal", "sourcePackageVersion": self.version,
                   "target": str(self.runtime), "files": entries}
        marker = self.runtime / ".atelier-installation.json"
        original = json.dumps(receipt).encode()
        marker.write_bytes(original)
        marker.chmod(0o600)
        with patch.object(service.subprocess, "run", side_effect=self.download):
            service.install_runtime(self.home, "/reviewed/bun")
        self.assertEqual(marker.read_bytes(), original)
        with patch.dict(os.environ, {}, clear=True), patch.object(service.subprocess, "run", side_effect=self.versions):
            service.prepare(self.home, self.source, self.root / "prepared-with-marker")
        receipt["files"][0]["sha256"] = "0" * 64
        marker.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "does not match"):
            service.verified_runtime(self.runtime)
        marker.write_bytes(original)
        (self.runtime / "unexpected.txt").write_text("unowned extra")
        with self.assertRaisesRegex(ValueError, "package bytes differ"):
            service.verified_runtime(self.runtime)

    def test_prepare_refuses_changed_package_before_executing_any_runtime(self):
        self.package(self.runtime)
        (self.runtime / "dist/cli.js").write_text("changed but still reports the same version")
        with patch.object(service.subprocess, "run") as runner:
            with self.assertRaisesRegex(ValueError, "package bytes differ"):
                service.prepare(self.home, self.source, self.root / "must-not-exist")
        runner.assert_not_called()
        self.assertFalse((self.root / "must-not-exist").exists())

    def test_symlink_runtime_and_parent_are_refused(self):
        other = self.root / "other"
        other.mkdir()
        (self.home / ".local").symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "parent must not be a symlink"):
            service.install_runtime(self.home, "/reviewed/bun")
        with self.assertRaisesRegex(ValueError, "ordinary directory"):
            service.runtime_tree(self.home / ".local")

    def test_writable_runtime_ancestor_blocks_install_and_prepare(self):
        self.package(self.runtime)
        parent = self.home / ".local/share/portless"
        parent.chmod(0o777)
        with patch.object(service.subprocess, "run") as runner:
            with self.assertRaisesRegex(ValueError, "Runtime parents"):
                service.install_runtime(self.home, "/reviewed/bun")
            with self.assertRaisesRegex(ValueError, "Runtime parents"):
                service.prepare(self.home, self.source, self.root / "must-not-exist")
        runner.assert_not_called()
        self.assertFalse((self.root / "must-not-exist").exists())

    def test_unowned_writable_or_linked_runtime_content_is_refused(self):
        self.package(self.runtime)
        with patch.object(service.os, "getuid", return_value=os.getuid() + 1):
            with self.assertRaisesRegex(ValueError, "owned by the invoking user"):
                service.runtime_tree(self.runtime)
        cli = self.runtime / "dist/cli.js"
        cli.chmod(0o666)
        with self.assertRaisesRegex(ValueError, "not writable by others"):
            service.runtime_tree(self.runtime)
        cli.unlink()
        cli.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "link or special file"):
            service.runtime_tree(self.runtime)

    def test_path_only_repair_preserves_state_arguments_and_live_plist(self):
        self.package(self.runtime)
        original = self.source.read_bytes()
        output = self.root / "prepared"
        with patch.dict(os.environ, {}, clear=True), patch.object(service.subprocess, "run", side_effect=self.versions):
            service.prepare(self.home, self.source, output)
        candidate = plistlib.loads((output / "candidate.plist").read_bytes())
        self.assertEqual(candidate["ProgramArguments"][2:], self.spec["ProgramArguments"][2:])
        self.assertEqual(candidate["ProgramArguments"][1], str(self.runtime / "dist/cli.js"))
        candidate["ProgramArguments"] = self.spec["ProgramArguments"]
        self.assertEqual(candidate, self.spec)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual((output / "original.plist").read_bytes(), original)
        self.assertFalse(json.loads((output / "receipt.json").read_text())["applied"])
        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        for path in output.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.home / ".portless").exists())

    def test_wrong_user_service_and_changed_node_fail_without_preparing(self):
        self.package(self.runtime)
        self.spec["EnvironmentVariables"]["HOME"] = "/different/user"
        self.source.write_bytes(plistlib.dumps(self.spec))
        with patch.dict(os.environ, {}, clear=True), patch.object(service.subprocess, "run", side_effect=self.versions):
            with self.assertRaisesRegex(ValueError, "Service identity"):
                service.prepare(self.home, self.source, self.root / "wrong-user")
        with patch.object(service.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "v999.0.0", "")):
            with self.assertRaisesRegex(ValueError, "reviewed global version"):
                service.prepare(self.home, self.source, self.root / "wrong-node")
        self.assertFalse((self.root / "wrong-user").exists())
        self.assertFalse((self.root / "wrong-node").exists())

    def test_failed_acquisition_leaves_no_runtime_or_staging(self):
        with patch.object(service.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["bun"])):
            with self.assertRaises(subprocess.CalledProcessError):
                service.install_runtime(self.home, "/reviewed/bun")
        self.assertFalse(self.runtime.exists())
        self.assertEqual(list(self.runtime.parent.iterdir()), [])

    def test_help_never_requires_bun_runtime_or_service(self):
        result = subprocess.run(["/usr/bin/env", "python3", str(REPO / "scripts/portless-service.py"), "--help"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn("install-runtime", result.stdout)
