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
REVIEW = json.loads((REPO / "tests/fixtures/codex-policy-review.json").read_text())
PREVIOUS = json.loads((REPO / "tests/fixtures/codex-policy-revision-2.json").read_text())
spec = importlib.util.spec_from_file_location("codex_rules", REPO / "scripts/codex-rules.py")
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)
CODEX = os.environ.get("CODEX_TEST_BINARY") or shutil.which("codex")


def staged_rules():
    actual = []
    for path in BUNDLE.glob("*.rules"):
        for node in ast.parse(path.read_text()).body:
            call = node.value
            assert call.func.id == "prefix_rule"
            actual.append({item.arg: ast.literal_eval(item.value) for item in call.keywords})
    return actual


def expanded(pattern):
    return itertools.product(*[part if isinstance(part, list) else [part] for part in pattern])


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

    def test_only_reviewed_denials_are_removed_and_all_other_rules_are_unchanged(self):
        actual = staged_rules()
        self.assertTrue(all(rule["decision"] in {"prompt", "forbidden"} for rule in actual))
        self.assertCountEqual(
            actual,
            [rule for rule in PREVIOUS["rules"] if rule["pattern"] not in REVIEW["retired_denials"]],
        )
        self.assertEqual(sum(rule["decision"] == "forbidden" for rule in actual), 2)
        self.assertCountEqual(
            [rule["pattern"] for rule in actual if rule["decision"] == "prompt"],
            REVIEW["global_prompts"],
        )
        metadata = json.loads((BUNDLE / "migration.json").read_text())
        self.assertEqual(metadata["legacy_sha256"], FIXTURE["source_sha256"])
        self.assertEqual(metadata["legacy_counts"], {"allow": 73, "prompt": 14, "forbidden": 5})
        self.assertEqual(metadata["staged_counts"], {"prompt": 8, "forbidden": 2})
        self.assertEqual(metadata["previous_policy"], {"policy_revision": 2, "files": PREVIOUS["files"]})
        self.assertEqual(len(actual), 10)
        self.assertEqual(rules.preview(self.home, self.bundle)["policy_revision"], 3)
        self.assertEqual(ast.parse((BUNDLE / "legacy-project.rules").read_text()).body, [])

    def test_previous_revision_is_a_conflict_and_is_never_silently_upgraded(self):
        for name in PREVIOUS["files"]:
            (self.active / name).write_text("# installed revision 2; preserve until activation\n")
        before = {p.name: p.read_bytes() for p in self.active.iterdir()}
        report = rules.preview(self.home, self.bundle)
        self.assertEqual(report["status"], "conflict")
        self.assertTrue(all(t["state"] == "conflict" for t in report["targets"]))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.active.iterdir()})

    @unittest.skipUnless(CODEX, "Native execpolicy checks require an existing Codex binary")
    def test_native_combinations_preserve_reviewed_boundaries_in_both_file_orders(self):
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
        reverse = [CODEX, "execpolicy", "check"]
        for name in reversed(sorted(rules.NAMES)):
            reverse += ["--rules", str(BUNDLE / name)]
        reverse += ["--rules", str(allowance)]
        for rule in staged_rules():
            for command in expanded(rule["pattern"]):
                for ordering in (prefix, reverse):
                    with self.subTest(command=command, ordering=ordering):
                        self.assertEqual(self.check(ordering, command), rule["decision"])
        # Removing a global denial does not override a stricter default/project layer.
        for pattern in REVIEW["retired_denials"]:
            for command in expanded(pattern):
                for ordering in (prefix, reverse):
                    with self.subTest(retired_command=command, ordering=ordering):
                        self.assertEqual(self.check(ordering, command), "allow")
        # The remaining project's stricter release-create denial must still win.
        project = self.home / "fixture-project.rules"
        project.write_text('prefix_rule(pattern = ["gh", "release", ["create", "edit", "delete"]], decision = "forbidden")\n')
        result = subprocess.run(prefix + ["--rules", str(project), "--", "gh", "release", "create", "v0.0.0"],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "forbidden")

    def check(self, prefix, command):
        result = subprocess.run(prefix + ["--", *command], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout).get("decision")

    @unittest.skipUnless(CODEX, "Native execpolicy checks require an existing Codex binary")
    def test_routine_and_project_prompts_fall_back_until_their_project_layer_is_loaded(self):
        prefix = [CODEX, "execpolicy", "check"]
        for name in sorted(rules.NAMES):
            prefix += ["--rules", str(BUNDLE / name)]
        commands = REVIEW["routine_commands"] + [list(c) for p in REVIEW["project_prompts"] + REVIEW["retired_denials"] for c in expanded(p)]
        for command in commands:
            with self.subTest(command=command):
                self.assertIsNone(self.check(prefix, command))
        project = self.home / "fixture-project-prompts.rules"
        project.write_text("\n".join(
            f"prefix_rule(pattern = {json.dumps(pattern)}, decision = 'prompt')"
            for pattern in REVIEW["project_prompts"]
        ))
        for pattern in REVIEW["project_prompts"]:
            for command in expanded(pattern):
                with self.subTest(project_command=command):
                    self.assertEqual(self.check(prefix + ["--rules", str(project)], command), "prompt")

    @unittest.skipUnless(CODEX, "Native execpolicy checks require an existing Codex binary")
    def test_removed_denials_still_defer_to_both_stricter_layer_decisions_and_orders(self):
        staged = [argument for name in sorted(rules.NAMES) for argument in ("--rules", str(BUNDLE / name))]
        for decision in ("prompt", "forbidden"):
            layer = self.home / "fixture-stricter.rules"
            layer.write_text("\n".join(
                f"prefix_rule(pattern = {json.dumps(pattern)}, decision = {json.dumps(decision)})"
                for pattern in REVIEW["retired_denials"]
            ))
            for arguments in (["--rules", str(layer), *staged], [*staged, "--rules", str(layer)]):
                for pattern in REVIEW["retired_denials"]:
                    for command in expanded(pattern):
                        with self.subTest(decision=decision, command=command, arguments=arguments):
                            self.assertEqual(self.check([CODEX, "execpolicy", "check", *arguments], command), decision)

    @unittest.skipUnless(CODEX, "Native execpolicy checks require an existing Codex binary")
    def test_unchanged_remembered_allowance_survives_prompt_removal(self):
        default = self.home / "fixture-remembered.rules"
        default.write_text('prefix_rule(pattern = ["uv"], decision = "allow")\n')
        prefix = [CODEX, "execpolicy", "check", "--rules", str(default)]
        for name in sorted(rules.NAMES):
            prefix += ["--rules", str(BUNDLE / name)]
        self.assertEqual(self.check(prefix, ["uv", "build"]), "allow")
        self.assertEqual(self.check(prefix, ["uv", "publish"]), "prompt")

    @unittest.skipUnless(CODEX, "Native execpolicy checks require an existing Codex binary")
    def test_old_restrictions_remain_effective_during_overlap_and_draft_edits_stay_denied(self):
        legacy = self.home / "fixture-legacy.rules"
        legacy.write_text("\n".join(
            f"prefix_rule(pattern = {json.dumps(rule['pattern'])}, decision = {json.dumps(rule['decision'])})"
            for rule in FIXTURE["restrictions"]
        ))
        prefix = [CODEX, "execpolicy", "check", "--rules", str(legacy)]
        for name in sorted(rules.NAMES):
            prefix += ["--rules", str(BUNDLE / name)]
        for rule in FIXTURE["restrictions"]:
            for command in expanded(rule["pattern"]):
                with self.subTest(command=command):
                    self.assertEqual(self.check(prefix, command), rule["decision"])
        for suffix in (["--draft"], ["--draft=false"], ["--prerelease"]):
            self.assertEqual(self.check(prefix, ["gh", "release", "edit", "v0.0.0", *suffix]), "forbidden")
