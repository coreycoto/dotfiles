"""Qualify staged policy independently of active host rules and provider accounts."""

import ast
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "home/dot_config/dotfiles/codex-rules"
FIXTURE = json.loads((REPO / "tests/fixtures/legacy-codex-boundaries.json").read_text())
spec = importlib.util.spec_from_file_location("codex_rules", REPO / "scripts/codex-rules.py")
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)
CODEX = os.environ.get("CODEX_TEST_BINARY") or shutil.which("codex")


def signature(rule):
    return json.dumps({"pattern": rule["pattern"], "decision": rule["decision"]}, sort_keys=True)


class CodexRuleTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.home = Path(self.scratch.name)
        self.active = self.home / ".codex/rules"
        self.active.mkdir(parents=True)
        self.legacy = self.active / "coreycoto.com.rules"
        self.legacy.write_text("# offline historical-file fixture\n")
        self.bundle = self.home / "staged"
        shutil.copytree(BUNDLE, self.bundle)
        metadata = json.loads((self.bundle / "migration.json").read_text())
        metadata["legacy_sha256"] = hashlib.sha256(self.legacy.read_bytes()).hexdigest()
        (self.bundle / "migration.json").write_text(json.dumps(metadata))
        (self.active / "default.rules").write_text("# remembered grants must survive\n")
        (self.active / "unrelated.rules").write_text("# local policy\n")
        (self.home / ".codex/config.toml").write_text('[hooks]\ntrust = "preserve"\n')

    def test_preview_preserves_all_existing_bytes_and_never_installs(self):
        before = {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        result = rules.preview(self.home, self.bundle)
        self.assertEqual(result["status"], "ready_for_review")
        self.assertFalse(result["applied"])
        after = {p.relative_to(self.home): p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertFalse((self.active / "personal.rules").exists())

    def test_ownership_missing_and_drift_are_unverified(self):
        self.legacy.write_text("# edited historical file\n")
        self.assertEqual(rules.preview(self.home, self.bundle)["status"], "legacy_unverified")
        self.legacy.unlink()
        self.assertEqual(rules.preview(self.home, self.bundle)["status"], "legacy_unverified")

    def test_target_conflicts_and_matching_owned_content(self):
        target = self.active / "personal.rules"
        target.write_text("# preserve my local edit\n")
        self.assertEqual(rules.preview(self.home, self.bundle)["status"], "conflict")
        self.assertEqual(target.read_text(), "# preserve my local edit\n")
        shutil.copyfile(self.bundle / "personal.rules", target)
        report = rules.preview(self.home, self.bundle)
        self.assertEqual(report["status"], "ready_for_review")
        self.assertIn("already_matches", [t["state"] for t in report["targets"]])

    def test_symlink_and_directory_destinations_are_conflicts(self):
        target = self.active / "personal.rules"
        target.symlink_to(self.legacy)
        self.assertEqual(rules.preview(self.home, self.bundle)["status"], "conflict")
        target.unlink()
        target.mkdir()
        self.assertEqual(rules.preview(self.home, self.bundle)["status"], "conflict")
        shutil.rmtree(self.active)
        self.active.write_text("# not a directory\n")
        self.assertEqual(rules.preview(self.home, self.bundle)["status"], "conflict")

    def test_staged_content_drift_is_rejected(self):
        with (self.bundle / "personal.rules").open("a") as stream:
            stream.write("# unreviewed source edit\n")
        with self.assertRaisesRegex(ValueError, "reviewed digest"):
            rules.preview(self.home, self.bundle)

    def test_invalid_ownership_manifest_cannot_make_missing_legacy_ready(self):
        self.legacy.unlink()
        path = self.bundle / "migration.json"
        metadata = json.loads(path.read_text())
        for value in (None, "", "not-a-digest"):
            metadata["legacy_sha256"] = value
            path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "Invalid migration digest"):
                rules.preview(self.home, self.bundle)

    def test_default_symlink_prevents_ready_status(self):
        default = self.active / "default.rules"
        default.unlink()
        default.symlink_to(self.legacy)
        self.assertEqual(rules.preview(self.home, self.bundle)["status"], "conflict")

    def test_cli_rejects_apply_without_writing(self):
        result = subprocess.run([shutil.which("python3"), str(REPO / "scripts/codex-rules.py"),
                                 "--home", str(self.home), "--apply"],
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)
        self.assertFalse((self.active / "personal.rules").exists())

    def test_all_historical_restrictions_survive_without_importing_allowances(self):
        actual = []
        for path in BUNDLE.glob("*.rules"):
            for node in ast.parse(path.read_text()).body:
                call = node.value
                self.assertEqual(call.func.id, "prefix_rule")
                data = {item.arg: ast.literal_eval(item.value) for item in call.keywords}
                self.assertIn(data["decision"], {"prompt", "forbidden"})
                actual.append(signature(data))
        self.assertCountEqual(actual, [signature(rule) for rule in FIXTURE["restrictions"]])
        metadata = json.loads((BUNDLE / "migration.json").read_text())
        self.assertEqual(metadata["legacy_sha256"], FIXTURE["source_sha256"])
        self.assertEqual(len(actual), 19)

    @unittest.skipUnless(CODEX, "Native execpolicy checks require an existing Codex binary")
    def test_native_combinations_preserve_every_boundary_despite_broad_local_allowances(self):
        # This synthetic default.rules is only an offline fixture, never the real home file.
        allowance = self.home / "fixture-default.rules"
        roots = {str(rule["pattern"][0]) for rule in FIXTURE["restrictions"]
                 if isinstance(rule["pattern"][0], str)} | {"agent-browser", "~/.bun/bin/agent-browser", "/Users/coreycoto/.bun/bin/agent-browser"}
        allowance.write_text("\n".join(
            f"prefix_rule(pattern = {json.dumps([root])}, decision = 'allow')" for root in sorted(roots)
        ))
        prefix = [CODEX, "execpolicy", "check", "--rules", str(allowance)]
        for name in sorted(rules.NAMES):
            prefix += ["--rules", str(BUNDLE / name)]
        count = 0
        for rule in FIXTURE["restrictions"]:
            choices = [part if isinstance(part, list) else [part] for part in rule["pattern"]]
            for command in itertools.product(*choices):
                with self.subTest(command=command):
                    result = subprocess.run(prefix + ["--", *command], text=True, capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["decision"], rule["decision"])
                    count += 1
        self.assertGreater(count, 40)
        # The remaining project's stricter release-create denial must still win.
        project = self.home / "fixture-project.rules"
        project.write_text('prefix_rule(pattern = ["gh", "release", ["create", "edit", "delete"]], decision = "forbidden")\n')
        result = subprocess.run(prefix + ["--rules", str(project), "--", "gh", "release", "create", "v0.0.0"],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "forbidden")
