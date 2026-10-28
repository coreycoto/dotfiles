"""Protect machine state while adding portable agent declarations."""

import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
LEGACY_SELECTION = REPO / "tests/fixtures/agent-plugins-v2.json"


def native_codex():
    """Resolve a Mise shim before native checks switch to a disposable home."""
    codex = shutil.which("codex")
    mise = shutil.which("mise")
    if codex and mise and Path(codex).resolve() == Path(mise).resolve():
        result = subprocess.run(
            [mise, "--cd", str(Path.home()), "which", "codex"],
            env=dict(os.environ, MISE_OFFLINE="1"),
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    return codex


CODEX_NATIVE = native_codex()


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="dotfiles-agent-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.home / ".codex/config.toml"
        self.config.parent.mkdir()
        self.config.write_text('''# machine-owned configuration
model = "gpt-5.6-sol"
[projects."/private-project"]
trust_level = "trusted"
[plugins."legacy@example"]
enabled = false
[mcp_servers.fixture]
command = "false"
[mcp_servers.fixture.env]
LOCAL_SENTINEL = "KEEP_LOCAL_STATE"
[auto_review]
policy = "KEEP_LOCAL_REVIEWER_POLICY"
extra_policy = "OLD_REVIEWER_SUPPLEMENT"
[desktop.open-in-target-preferences.perPath]
"/private-project" = "KEEP_LOCAL_EDITOR"
[features]
local_extra_switch = true
[memories]
local_extra_switch = true
''')
        self.original = self.config.read_bytes()

    def command(self, script, *args):
        return subprocess.run(
            [shutil.which("python3"), str(REPO / "scripts" / script), "--home", str(self.home), *args],
            capture_output=True, text=True, timeout=45,
        )

    def rendered_preferences(self):
        module = load_script("codex-preferences")
        return module.preference_text(module.DEFAULT_PREFERENCES)

    def apply_home(self, source=REPO):
        options = self.root / "chezmoi.json"
        options.write_text("{}\n")
        command = [
            shutil.which("chezmoi"), "--source", str(source), "--destination", str(self.home),
            "--config", str(options), "--persistent-state", str(self.root / "state.db"),
            "--cache", str(self.root / "cache"), "--no-tty", "apply", "--force",
        ]
        result = subprocess.run(command, env=dict(os.environ, HOME=str(self.home)),
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_agent_manifest_excludes_machine_state(self):
        files = json.loads((REPO / "manifest.json").read_text())["files"]
        codex_targets = {entry["target"] for entry in files if Path(entry["target"]).parts[0] == ".codex"}
        self.assertEqual(codex_targets, {
            ".codex/AGENTS.md", ".codex/autonomy-policy.md", ".codex/preferences.toml",
        })

    def test_preference_preview_is_read_only_and_does_not_display_machine_state(self):
        result = self.command("codex-preferences.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["applied"])
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertNotIn("KEEP_LOCAL_STATE", result.stdout + result.stderr)
        self.assertNotIn("private-project", result.stdout + result.stderr)
        self.assertFalse((self.home / ".local").exists())

    def test_combined_setup_stops_before_writes_when_plugin_preview_fails(self):
        module = load_script("codex-setup")
        calls = []

        def runner(command, **_):
            calls.append(command)
            failed = "agent-plugins.py" in command[1]
            return subprocess.CompletedProcess(command, 2 if failed else 0,
                                               "" if failed else '{"applied": false}', "")

        report, code = module.setup(self.home, "codex", True, runner=runner)
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("--apply" not in command for command in calls))
        self.assertEqual(report["status"], "failed")
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_combined_setup_keeps_partial_receipt_and_never_retries(self):
        module = load_script("codex-setup")
        calls = []

        def runner(command, **_):
            calls.append(command)
            failed = "agent-plugins.py" in command[1] and "--apply" in command
            receipt = {"applied": "--apply" in command and not failed}
            if failed:
                receipt["completed_actions"] = [{"kind": "marketplace_add"}]
                receipt["failed_action"] = {"kind": "plugin_add"}
            return subprocess.CompletedProcess(command, 2 if failed else 0,
                                               json.dumps(receipt), "PRIVATE_DIAGNOSTIC")

        report, code = module.setup(self.home, "codex", True, runner=runner)
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 4)
        self.assertTrue(report["steps"][2]["receipt"]["applied"])
        self.assertEqual(report["failed_step"]["receipt"]["completed_actions"],
                         [{"kind": "marketplace_add"}])
        self.assertFalse(report["applied"])
        self.assertNotIn("PRIVATE_DIAGNOSTIC", json.dumps(report))

    def test_combined_setup_preview_preserves_existing_home(self):
        fake = self.root / "codex"
        fake.write_text('''#!/usr/bin/env python3
import json,sys
if sys.argv[1:] == ['--version']:
    print('codex-cli 0.162.0')
elif sys.argv[1:] == ['plugin','list','--json']:
    print(json.dumps({'installed': [], 'available': []}))
else:
    raise SystemExit('Unexpected mutation')
''')
        fake.chmod(0o755)
        result = self.command("codex-setup.py", "--codex", str(fake))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "preview")
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local").exists())

    def test_preferences_reject_permission_and_connection_imports(self):
        path = self.root / "unreviewed.toml"
        source = self.rendered_preferences()
        cases = (
            source.replace('approval_policy = "on-request"', 'approval_policy = "never"'),
            source.replace('default_permissions = ":workspace"', 'default_permissions = "personal-workspace"'),
            source + '\n[permissions.local.workspace_roots]\n"/private-project" = true\n',
            source.replace('js_repl = false', 'js_repl = 0'),
            source + '\n[mcp_servers.private]\ncommand = "false"\n',
        )
        for content in cases:
            path.write_text(content)
            result = self.command("codex-preferences.py", "--preferences", str(path), "--apply")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(self.config.read_bytes(), self.original)

    @unittest.skipUnless(CODEX_NATIVE, "Native Codex integration is verified separately when available")
    def test_native_preference_merge_preserves_other_keys_and_private_backup(self):
        result = self.command("codex-preferences.py", "--codex", CODEX_NATIVE, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["applied"])
        before = tomllib.loads(self.original.decode())
        desired = tomllib.loads(self.rendered_preferences())
        expected = dict(before, **desired)
        for table in ("auto_review", "desktop", "features", "memories"):
            expected[table] = dict(before.get(table, {}), **desired[table])
        self.assertEqual(tomllib.loads(self.config.read_text()), expected)
        self.assertIn("auto_review.extra_policy", report["changed_keys"])
        self.assertIn("# machine-owned configuration", self.config.read_text())
        backup = Path(report["backup"]) / "config.toml"
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("KEEP_LOCAL_STATE", result.stdout + result.stderr)
        again = self.command("codex-preferences.py", "--codex", CODEX_NATIVE, "--apply")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(json.loads(again.stdout)["changed_keys"], [])

    def test_preference_merge_rejects_symlink_target(self):
        destination = self.root / "external.toml"
        destination.write_bytes(self.original)
        self.config.unlink()
        self.config.symlink_to(destination)
        result = self.command("codex-preferences.py", "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(destination.read_bytes(), self.original)

    @unittest.skipUnless(CODEX_NATIVE, "Native Codex integration is verified separately when available")
    def test_native_preference_merge_supports_a_fresh_home(self):
        fresh = self.root / "first-home"
        fresh.mkdir()
        command = [shutil.which("python3"), str(REPO / "scripts/codex-preferences.py"),
                   "--home", str(fresh), "--codex", CODEX_NATIVE]
        preview = subprocess.run(command, capture_output=True, text=True, timeout=45)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(list(fresh.iterdir()), [])
        applied = subprocess.run(command + ["--apply"], capture_output=True, text=True, timeout=45)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        desired = tomllib.loads(self.rendered_preferences())
        self.assertEqual(tomllib.loads((fresh / ".codex/config.toml").read_text()), desired)
        self.assertEqual((fresh / ".codex").stat().st_mode & 0o777, 0o700)

    def test_preference_input_rejects_replacement_policy_and_invalid_supplements(self):
        defaults = self.rendered_preferences().split("[auto_review]")[0]
        path = self.root / "unreviewed.toml"
        cases = (
            'policy = "replacement"\n',
            'extra_policy = "additive"\npolicy = "replacement"\n',
            'extra_policy = ""\n',
            'extra_policy = 42\n',
        )
        for review in cases:
            with self.subTest(review=review):
                path.write_text(defaults + "[auto_review]\n" + review)
                result = self.command("codex-preferences.py", "--preferences", str(path), "--apply")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local").exists())

    def test_old_or_unknown_codex_is_rejected_before_mutation(self):
        fake = self.root / "codex"
        for version in ("codex-cli 0.159.0", "unknown-client"):
            with self.subTest(version=version):
                fake.write_text('#!/bin/sh\n[ "$1" = "--version" ] || exit 9\nprintf "%s\\n" "' + version + '"\n')
                fake.chmod(0o755)
                result = self.command("codex-preferences.py", "--codex", str(fake), "--apply")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local").exists())

    def test_policy_changes_update_global_guidance_without_expanding_reviewer_hint(self):
        source = self.root / "render-source"
        shutil.copytree(REPO / "home", source / "home")
        (source / ".chezmoiroot").write_text("home\n")
        policy = (source / "home/dot_codex/autonomy-policy.md").read_text()
        policy += '\nLiteral "quotes", triple """ quotes, C:\\scratch, Unicode café, and {{ template syntax }}.\n'
        (source / "home/dot_codex/autonomy-policy.md").write_text(policy)
        hint = tomllib.loads(self.rendered_preferences())["auto_review"]["extra_policy"]
        self.assertIn("parent's applied global and thread guidance", hint)
        self.assertIn("`AGENTS.override.md` or `AGENTS.md`", hint)
        self.assertIn("`$CODEX_HOME` (default `~/.codex`)", hint)
        for current in (policy, policy + "\nChanged authored guidance.\n"):
            (source / "home/dot_codex/autonomy-policy.md").write_text(current)
            self.apply_home(source)
            rendered = tomllib.loads((self.home / ".codex/preferences.toml").read_text())
            self.assertEqual(set(rendered["auto_review"]), {"extra_policy"})
            self.assertEqual(rendered["auto_review"]["extra_policy"], hint)
            self.assertNotIn(current.strip(), hint)
            self.assertIn(current, (self.home / ".codex/AGENTS.md").read_text())
            self.assertEqual((self.home / ".codex/autonomy-policy.md").read_text(), current)
        self.assertEqual(self.config.read_bytes(), self.original)

    @unittest.skipUnless(CODEX_NATIVE, "Native instruction discovery is verified separately when available")
    def test_native_global_guidance_respects_custom_home_and_override_precedence(self):
        self.apply_home()
        custom = self.root / "custom codex home"
        custom.mkdir()
        (custom / "AGENTS.md").write_text("CUSTOM_GLOBAL_GUIDANCE\n")
        override = custom / "AGENTS.override.md"
        cases = (
            (None, None, (REPO / "home/dot_codex/autonomy-policy.md").read_text().strip(), "CUSTOM_GLOBAL_GUIDANCE"),
            (custom, None, "CUSTOM_GLOBAL_GUIDANCE", "Honor the user's authorized scope"),
            (custom, "OVERRIDE_GLOBAL_GUIDANCE\n", "OVERRIDE_GLOBAL_GUIDANCE", "CUSTOM_GLOBAL_GUIDANCE"),
            (custom, "", "CUSTOM_GLOBAL_GUIDANCE", "OVERRIDE_GLOBAL_GUIDANCE"),
        )
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from strings(child)
            elif isinstance(value, list):
                for child in value:
                    yield from strings(child)
        for codex_home, contents, included, excluded in cases:
            with self.subTest(codex_home=codex_home, override=contents):
                if contents is not None:
                    override.write_text(contents)
                env = dict(os.environ, HOME=str(self.home))
                env.pop("CODEX_HOME", None)
                if codex_home:
                    env["CODEX_HOME"] = str(codex_home)
                result = subprocess.run(
                    [CODEX_NATIVE, "debug", "prompt-input", "Inspect local instructions."],
                    cwd=self.home, env=env, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                prompt = "\n".join(strings(json.loads(result.stdout)))
                self.assertIn(included, prompt)
                self.assertNotIn(excluded, prompt)
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_plugin_declaration_requires_credentials_free_immutable_sources(self):
        module = load_script("agent-plugins")
        original = json.loads((LEGACY_SELECTION).read_text())
        path = self.root / "selection.json"
        path.write_text(json.dumps(original))
        module.manifest(path)
        for key, value in (("ref", "main"), ("url", "https://user:password@github.com/example/plugins.git")):
            data = json.loads(json.dumps(original))
            data["marketplaces"][0][key] = value
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                module.manifest(path)
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_native_git_preview_has_no_home_writes_or_bundle_migration(self):
        module = load_script("agent-plugins")
        desired = module.manifest(REPO / "home/dot_config/dotfiles/agent-plugins.json")
        self.assertEqual(desired["version"], 3)
        report = module.bootstrap(self.home, desired, str(self.version_and_inventory_codex()), False)
        self.assertEqual([a["source"] for a in report["planned_actions"] if a["kind"] == "verify_source"],
                         ["agent-plugins"])
        self.assertFalse(any(a["kind"] in {"build", "plugin_remove", "marketplace_remove"}
                             for a in report["planned_actions"]))
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local").exists())
        source = desired["marketplaces"][0]
        source["url"] = "https://user:password@github.com/example/plugins.git"
        bad = self.root / "bad-native.json"
        bad.write_text(json.dumps(desired))
        with self.assertRaises(ValueError):
            module.manifest(bad)
        source["url"] = "https://github.com/example/plugins.git"
        source["sparse_paths"] = ["../private"]
        bad.write_text(json.dumps(desired))
        with self.assertRaisesRegex(ValueError, "catalog directory"):
            module.manifest(bad)

    def test_local_catalogs_require_explicit_adoption_and_remember_enabled_selection(self):
        local_path = self.home / ".config/dotfiles/agent-plugin-sources.local.json"
        local_path.parent.mkdir(parents=True)
        local_path.write_bytes((REPO / "examples/agent-plugin-sources.example.json").read_bytes())
        before = local_path.read_bytes()
        public_path = REPO / "home/dot_config/dotfiles/agent-plugins.json"
        public_before = public_path.read_bytes()
        fake = self.version_and_inventory_codex()
        for flags, expected in (((), ["agent-plugins"]),
                                (("--private",), ["agent-plugins", "my-local-plugins"])):
            result = self.command("agent-plugins.py", "--codex", str(fake), *flags)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual([a["source"] for a in report["planned_actions"]
                              if a["kind"] == "verify_source"], expected)
            self.assertFalse(report["applied"])
        installed = {"installed": [{"name": "example-plugin", "marketplaceName": "my-local-plugins",
                                   "version": "1.0.0", "enabled": True}], "available": []}
        fake.write_text(fake.read_text().replace("json.dumps({'installed': [], 'available': []})",
                                                repr(json.dumps(installed))))
        result = self.command("agent-plugins.py", "--codex", str(fake))
        self.assertEqual(result.returncode, 0, result.stderr)
        actions = json.loads(result.stdout)["planned_actions"]
        self.assertEqual([a["source"] for a in actions if a["kind"] == "verify_source"],
                         ["agent-plugins", "my-local-plugins"])
        self.assertEqual(local_path.read_bytes(), before)
        self.assertEqual(public_path.read_bytes(), public_before)
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local").exists())

    def test_local_catalog_errors_stop_apply_before_native_commands_or_writes(self):
        source = json.loads((REPO / "examples/agent-plugin-sources.example.json").read_text())["marketplaces"][0]
        local_path = self.root / "sources.local.json"
        invalid = [
            {"unexpected": []},
            {"marketplaces": {}},
            {"marketplaces": [dict(source, optional=False)]},
            {"marketplaces": [dict(source, name="agent-plugins")]},
            {"marketplaces": [dict(source, ref="main")]},
            {"marketplaces": [dict(source, url="https://user:password@github.com/example/plugins.git")]},
        ]
        for value in invalid:
            with self.subTest(value=value):
                local_path.write_text(json.dumps(value))
                result = self.command("agent-plugins.py", "--apply", "--codex", "/missing/codex",
                                      "--local-manifest", str(local_path))
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("user:password", result.stdout + result.stderr)
                self.assertEqual(self.config.read_bytes(), self.original)
                self.assertFalse((self.home / ".local").exists())

    def test_local_catalog_overlay_requires_native_manifest_and_missing_file_is_optional(self):
        module = load_script("agent-plugins")
        public = REPO / "home/dot_config/dotfiles/agent-plugins.json"
        self.assertEqual(module.manifest(public, self.root / "absent.local.json"), module.manifest(public))
        local_path = REPO / "examples/agent-plugin-sources.example.json"
        with self.assertRaisesRegex(ValueError, "version-3"):
            module.manifest(LEGACY_SELECTION, local_path)

    def test_explicit_missing_local_catalog_file_stops_before_apply(self):
        result = self.command("agent-plugins.py", "--apply", "--codex", "/missing/codex",
                              "--local-manifest", str(self.root / "missing.local.json"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("--local-manifest must name an existing file", result.stderr)
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local").exists())

    def test_mise_resolution_is_offline_and_never_executes_the_shim(self):
        module = load_script("agent-plugins")
        native = self.root / "installed-codex"
        native.write_text('#!/bin/sh\nexit 99\n')
        native.chmod(0o755)
        mise = self.root / "mise"
        mise.write_text('#!/bin/sh\n[ "$MISE_OFFLINE" = 1 ] || exit 9\n'
                        '[ "$3" = which ] && [ "$4" = codex ] || exit 10\n'
                        'printf "%s\\n" "' + str(native) + '"\n')
        mise.chmod(0o755)
        shim = self.root / "codex"
        shim.symlink_to(mise)
        with mock.patch.dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ["PATH"]):
            self.assertEqual(module.resolve_codex(str(shim)), str(native))
            native.unlink()
            with self.assertRaisesRegex(ValueError, "install it explicitly"):
                module.resolve_codex(str(shim))

    def native_package_fixture(self):
        module = load_script("agent-plugins")
        desired = module.manifest(REPO / "home/dot_config/dotfiles/agent-plugins.json")
        source = desired["marketplaces"][0]
        publisher = self.root / "reviewed-publisher"
        installed = {}
        for name, version in source["plugins"].items():
            package = publisher / "plugins" / name / "skills/check/SKILL.md"
            package.parent.mkdir(parents=True)
            package.write_text("independently reviewed fixture instructions\n")
            target = self.home / ".codex/plugins/cache" / source["name"] / name / version
            shutil.copytree(package.parents[2], target)
            installed[f"{name}@{source['name']}"] = {
                "name": name, "marketplaceName": source["name"], "version": version, "enabled": True,
            }
        return module, desired, source, publisher, installed

    @unittest.skipUnless(CODEX_NATIVE, "Native Codex integration is verified separately when available")
    def test_native_git_pin_preserves_legacy_reviewer(self):
        module, desired, source, publisher, installed = self.native_package_fixture()
        self.config.write_text('approvals_reviewer = "guardian_subagent"\n' + self.config.read_text())
        before = tomllib.loads(self.config.read_text())
        with mock.patch.dict(module.bootstrap_native.__globals__,
                             run=lambda *_args, **_kwargs: "codex-cli 0.162.1",
                             inventory=lambda *_: installed,
                             source_checkout=lambda *_: publisher,
                             build=lambda _home, _source, dest: shutil.copytree(publisher, dest)):
            report = module.bootstrap(self.home.resolve(), desired, CODEX_NATIVE, True)
        self.assertTrue(report["applied"])
        after = tomllib.loads(self.config.read_text())
        self.assertEqual(after["marketplaces"][source["name"]]["ref_name"], source["ref"])
        self.assertEqual({k: v for k, v in after.items() if k != "marketplaces"}, before)

    def test_native_config_guard_rejects_drift_before_write(self):
        module = load_script("agent-plugins")
        self.config.write_text('approvals_reviewer = "guardian_subagent"\n' + self.config.read_text())
        before = tomllib.loads(self.config.read_text())
        for drift in ("unrelated", "reviewer"):
            with self.subTest(drift=drift):
                self.config.write_text('approvals_reviewer = "guardian_subagent"\n' + self.original.decode())
                observed = dict(before, approvals_reviewer="auto_review")
                calls = []

                class FakeRpc:
                    def __init__(self, *_):
                        self.process = mock.Mock()
                    def call(self, method, _params):
                        calls.append(method)
                        if method == "config/read":
                            if drift == "unrelated":
                                observed["model"] = "changed"
                            else:
                                self_config = self_path.read_text().replace("guardian_subagent", "auto_review")
                                self_path.write_text(self_config)
                            return {"layers": [{"name": {"type": "user", "file": str(self_path)},
                                                "config": observed, "version": "fixture"}]}
                        return {}
                    def close(self):
                        pass

                self_path = self.config
                with mock.patch.dict(module.native_config_write.__globals__, Rpc=FakeRpc):
                    with self.assertRaisesRegex(ValueError, "configuration changed"):
                        module.native_config_write(self.home, "codex", before, {"marketplaces.fixture": {}})
                self.assertNotIn("config/batchWrite", calls)

    @unittest.skipUnless(CODEX_NATIVE, "Native Codex integration is verified separately when available")
    def test_native_git_pin_preserves_settings_and_matching_packages(self):
        module, desired, source, publisher, installed = self.native_package_fixture()
        calls = []

        def run(args, *_args, **_kwargs):
            calls.append(args)
            self.assertEqual(args[1:], ["--version"])
            return "codex-cli 0.162.1"

        before = tomllib.loads(self.config.read_text())
        namespace = module.bootstrap_native.__globals__
        with mock.patch.dict(namespace, run=run, inventory=lambda *_: installed,
                             source_checkout=lambda *_: publisher,
                             build=lambda _home, _source, dest: shutil.copytree(publisher, dest)):
            report = module.bootstrap(self.home.resolve(), desired, CODEX_NATIVE, True)
        self.assertTrue(report["applied"])
        self.assertEqual(len(report["verified_plugins"]), len(source["plugins"]))
        self.assertEqual(len(calls), 1)
        after = tomllib.loads(self.config.read_text())
        self.assertEqual(after["marketplaces"][source["name"]]["ref_name"], source["ref"])
        self.assertEqual({k:v for k,v in after.items() if k != "marketplaces"}, before)
        self.assertEqual(Path(report["backup"]).joinpath(".codex/config.toml").read_bytes(), self.original)

    @unittest.skipUnless(CODEX_NATIVE, "Native Codex integration is verified separately when available")
    def test_native_git_install_failure_retains_partial_receipt_without_retry(self):
        module, desired, _source, publisher, _installed = self.native_package_fixture()
        calls = []

        def run(args, *_args, **_kwargs):
            calls.append(args)
            if args[1:] == ["--version"]:
                return "codex-cli 0.162.1"
            raise ValueError("fixture install failure")

        output = io.StringIO()
        with mock.patch.dict(module.bootstrap_native.__globals__, run=run, inventory=lambda *_: {},
                             source_checkout=lambda *_: publisher,
                             build=lambda _home, _source, dest: shutil.copytree(publisher, dest)), \
                contextlib.redirect_stdout(output), self.assertRaisesRegex(ValueError, "retain this partial receipt"):
            module.bootstrap(self.home.resolve(), desired, CODEX_NATIVE, True)
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["failed_action"]["kind"], "plugin_add")
        self.assertEqual(sum(a[1:3] == ["plugin", "add"] for a in calls), 1)
        self.assertIn({"kind": "configure_marketplaces"}, receipt["completed_actions"])
        self.assertNotIn("KEEP_LOCAL_STATE", output.getvalue())

    @unittest.skipUnless(CODEX_NATIVE, "Native Codex integration is verified separately when available")
    def test_native_permission_retirement_keeps_other_configuration(self):
        module = load_script("agent-plugins")
        self.config.write_text('default_permissions = "personal-workspace"\n' + self.config.read_text()
                               + '\n[permissions.personal-workspace]\nextends = ":workspace"\n')
        before = tomllib.loads(self.config.read_text())
        after = module.native_config_write(self.home, CODEX_NATIVE, before,
                                          {"default_permissions": ":workspace", "permissions": None})
        self.assertEqual(after["default_permissions"], ":workspace")
        self.assertNotIn("permissions", after)
        self.assertEqual({k:v for k,v in after.items() if k != "default_permissions"},
                         {k:v for k,v in before.items() if k not in {"permissions", "default_permissions"}})

    def pinned_marketplace(self):
        root = self.root / "publisher"
        root.mkdir()
        (root / "tracked.txt").write_text("reviewed source\n")
        env = dict(os.environ, HOME=str(self.home))
        for args in (
            ["init", "--quiet"], ["add", "tracked.txt"],
            ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Reviewed source"],
        ):
            subprocess.run(["git", "-C", str(root), *args], env=env,
                           check=True, capture_output=True, text=True)
        revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                  env=env, check=True, capture_output=True, text=True).stdout.strip()
        source = {"url": "https://github.com/example/plugins.git", "ref": revision}
        metadata = {"source_type": "git", "source": source["url"],
                    "ref_name": revision, "sparse_paths": [], "revision": revision}
        marker = root / ".codex-marketplace-install.json"
        marker.write_text(json.dumps(metadata))
        return root, source, marker, metadata

    def test_checkout_accepts_matching_native_metadata_without_changing_it(self):
        module = load_script("agent-plugins")
        root, source, marker, _ = self.pinned_marketplace()
        original = marker.read_bytes()
        module.verify_checkout(root, self.home, source)
        (root / ".git/info/exclude").write_text(marker.name + "\n")
        module.verify_checkout(root, self.home, source)
        self.assertEqual(marker.read_bytes(), original)

    def test_checkout_rejects_mismatched_or_malformed_native_metadata(self):
        module = load_script("agent-plugins")
        root, source, marker, metadata = self.pinned_marketplace()
        for field, value in (("source_type", "local"), ("source", "https://github.com/example/other.git"),
                             ("ref_name", "main"), ("revision", "0" * 40),
                             ("sparse_paths", ["plugins/example"]), ("unexpected", True)):
            with self.subTest(field=field):
                marker.write_text(json.dumps(dict(metadata, **{field: value})))
                with self.assertRaises(ValueError):
                    module.verify_checkout(root, self.home, source)
        marker.write_text("invalid JSON\n")
        with self.assertRaises(ValueError):
            module.verify_checkout(root, self.home, source)

    def test_checkout_rejects_symlinked_native_metadata(self):
        module = load_script("agent-plugins")
        root, source, marker, metadata = self.pinned_marketplace()
        outside = self.root / "metadata.json"
        outside.write_text(json.dumps(metadata))
        marker.unlink()
        marker.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "regular"):
            module.verify_checkout(root, self.home, source)

    def test_native_metadata_does_not_hide_source_or_revision_drift(self):
        module = load_script("agent-plugins")
        root, source, _, _ = self.pinned_marketplace()
        extra = root / "unexpected.txt"
        extra.write_text("unexpected\n")
        with self.assertRaises(ValueError):
            module.verify_checkout(root, self.home, source)
        extra.unlink()
        (root / "tracked.txt").write_text("changed source\n")
        with self.assertRaises(ValueError):
            module.verify_checkout(root, self.home, source)
        (root / "tracked.txt").write_text("reviewed source\n")
        (root / ".git/info/exclude").write_text(extra.name + "\n")
        extra.write_text("ignored but unexpected\n")
        with self.assertRaises(ValueError):
            module.verify_checkout(root, self.home, source)
        extra.unlink()
        with self.assertRaises(ValueError):
            module.verify_checkout(root, self.home, dict(source, ref="0" * 40))

    def test_existing_disabled_plugin_is_preserved_without_mutation(self):
        module = load_script("agent-plugins")
        desired = module.manifest(LEGACY_SELECTION)
        self.config.write_text('[plugins."project-management@agent-plugins"]\nenabled = false\n')
        before = self.config.read_bytes()
        fake = self.root / "codex"
        fake.write_text('''#!/usr/bin/env python3
import json,sys
if sys.argv[1:] == ['--version']:
    print('codex-cli 0.162.0')
elif sys.argv[1:] == ['plugin','list','--json']:
    print(json.dumps({'installed': [], 'available': []}))
else:
    raise SystemExit('Unexpected mutation')
''')
        fake.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "disabled"):
            module.bootstrap(self.home, desired, str(fake), True)
        self.assertEqual(self.config.read_bytes(), before)

    def test_fresh_home_preview_does_not_create_codex_state(self):
        module = load_script("agent-plugins")
        desired = module.manifest(LEGACY_SELECTION)
        fresh = self.root / "fresh-home"
        fresh.mkdir()
        fake = self.root / "version-only-codex"
        fake.write_text('#!/bin/sh\n[ "$1" = "--version" ] || exit 9\nprintf "codex-cli 0.160.0\\n"\n')
        fake.chmod(0o755)
        report = module.bootstrap(fresh, desired, str(fake), False)
        self.assertEqual([x["kind"] for x in report["planned_actions"]],
                         ["build", "marketplace_add", "plugin_add", "plugin_add"])
        self.assertEqual(list(fresh.iterdir()), [])

    def test_cached_package_rejects_changed_and_undeclared_skill_content(self):
        module = load_script("agent-plugins")
        publisher = self.root / "publisher"
        source = {"name": "fixture"}
        expected = publisher / "plugins/example/skills/check/SKILL.md"
        cached = self.home / ".codex/plugins/cache/fixture/example/1.0.0/skills/check/SKILL.md"
        for p in (expected, cached):
            p.parent.mkdir(parents=True)
            p.write_text("reviewed instructions\n")
        package = {"packages": {"example": str(publisher / "plugins/example")}}
        module.verify_cached_package(self.home, source, package, "example", "1.0.0")
        cached.write_text("changed instructions\n")
        with self.assertRaises(ValueError):
            module.verify_cached_package(self.home, source, package, "example", "1.0.0")
        cached.write_text(expected.read_text())
        extra = cached.parent.parent / "unexpected/SKILL.md"
        extra.parent.mkdir()
        extra.write_text("undeclared skill\n")
        with self.assertRaises(ValueError):
            module.verify_cached_package(self.home, source, package, "example", "1.0.0")

    def version_and_inventory_codex(self):
        fake = self.root / "codex-preview"
        fake.write_text('''#!/usr/bin/env python3
import json,sys
if sys.argv[1:] == ['--version']:
    print('codex-cli 0.162.0')
elif sys.argv[1:] == ['plugin','list','--json']:
    print(json.dumps({'installed': [], 'available': []}))
else:
    raise SystemExit('Unexpected mutation')
''')
        fake.chmod(0o755)
        return fake

    def test_installed_updater_previews_from_outside_checkout_without_writes(self):
        self.apply_home()
        executable = self.home / ".local/bin/dotfiles-plugins"
        result = subprocess.run([str(executable), "--codex", str(self.version_and_inventory_codex())],
                                cwd=self.root, env=dict(os.environ, HOME=str(self.home)),
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["applied"])
        self.assertFalse(report["registry_publication_required"])
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_private_adoption_is_explicit_on_a_fresh_machine(self):
        module = load_script("agent-plugins")
        desired = module.manifest(LEGACY_SELECTION)
        fake = str(self.version_and_inventory_codex())
        public = module.bootstrap(self.home, desired, fake, False)
        private = module.bootstrap(self.home, desired, fake, False, include_private=True)
        self.assertEqual([x["source"] for x in public["planned_actions"] if x["kind"] == "build"],
                         ["agent-plugins"])
        self.assertEqual([x["source"] for x in private["planned_actions"] if x["kind"] == "build"],
                         ["agent-plugins", "optional-plugins"])
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_unowned_bundle_is_preserved_before_any_install(self):
        module = load_script("agent-plugins")
        desired = module.manifest(LEGACY_SELECTION)
        sentinel = self.home / ".local/share/agent-plugins/codex-public/keep.txt"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("KEEP_LOCAL_STATE\n")
        with self.assertRaisesRegex(ValueError, "unowned"):
            module.bootstrap(self.home, desired, str(self.version_and_inventory_codex()), True)
        self.assertEqual(sentinel.read_text(), "KEEP_LOCAL_STATE\n")
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_unknown_same_name_catalog_is_preserved(self):
        module = load_script("agent-plugins")
        desired = module.manifest(LEGACY_SELECTION)
        self.config.write_text('[marketplaces.agent-plugins]\nsource_type = "local"\nsource = "/other/local/catalog"\n')
        original = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, "unreviewed source"):
            module.bootstrap(self.home, desired, str(self.version_and_inventory_codex()), True)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_disabled_optional_private_plugin_and_its_catalog_are_preserved(self):
        module = load_script("agent-plugins")
        desired = module.manifest(LEGACY_SELECTION)
        self.config.write_text('[marketplaces.optional-plugins]\nsource_type = "local"\n'
                               'source = "/private/local/catalog"\n'
                               '[plugins."optional-plugin@optional-plugins"]\nenabled = false\n')
        original = self.config.read_bytes()
        fake = self.version_and_inventory_codex()
        data = {'installed': [{'name': 'optional-plugin', 'marketplaceName': 'optional-plugins',
                               'version': '1.0.0', 'enabled': False}], 'available': []}
        fake.write_text(fake.read_text().replace("json.dumps({'installed': [], 'available': []})", repr(json.dumps(data))))
        report = module.bootstrap(self.home, desired, str(fake), False)
        self.assertFalse(any(a.get('name') == 'optional-plugins' for a in report['planned_actions']))
        self.assertEqual(self.config.read_bytes(), original)

    def pilot_catalog_fixture(self, installed=()):
        self.config.write_text('[marketplaces.agent-plugins-pr3-pilot]\n'
                               'source_type = "local"\nsource = "/reviewed/local/pilot"\n')
        fake = self.version_and_inventory_codex()
        data = {'installed': list(installed), 'available': []}
        fake.write_text(fake.read_text().replace("json.dumps({'installed': [], 'available': []})", repr(json.dumps(data))))
        return load_script("agent-plugins"), str(fake), self.config.read_bytes()

    def test_legacy_only_catalog_requires_reviewed_source_before_mutation(self):
        module, fake, original = self.pilot_catalog_fixture()
        desired = module.manifest(LEGACY_SELECTION)
        with self.assertRaisesRegex(ValueError, "source is unreviewed"):
            module.bootstrap(self.home, desired, fake, True)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_repurposed_pilot_catalog_is_preserved_with_or_without_stale_plugin(self):
        stale = {'name': 'product-development', 'marketplaceName': 'agent-plugins-pr3-pilot',
                 'version': '0.8.0', 'enabled': True}
        for installed in ((), (stale,)):
            with self.subTest(stale_plugin=bool(installed)):
                module, fake, original = self.pilot_catalog_fixture(installed)
                desired = module.manifest(LEGACY_SELECTION)
                with self.assertRaisesRegex(ValueError, "differs from the reviewed"):
                    module.bootstrap(self.home, desired, fake, True, retire_pilot_path="/other/expected/pilot")
                self.assertEqual(self.config.read_bytes(), original)
                self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_matching_reviewed_pilot_source_allows_known_migration_preview(self):
        stale = {'name': 'product-development', 'marketplaceName': 'agent-plugins-pr3-pilot',
                 'version': '0.8.0', 'enabled': True}
        module, fake, original = self.pilot_catalog_fixture((stale,))
        desired = module.manifest(LEGACY_SELECTION)
        report = module.bootstrap(self.home, desired, fake, False, retire_pilot_path="/reviewed/local/pilot")
        self.assertIn({'kind': 'marketplace_remove', 'name': 'agent-plugins-pr3-pilot'}, report['planned_actions'])
        self.assertIn({'kind': 'plugin_remove', 'plugin_id': module.PILOT_SELECTOR}, report['planned_actions'])
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_matching_pilot_source_does_not_allow_unrelated_plugin_removal(self):
        unrelated = {'name': 'other-plugin', 'marketplaceName': 'agent-plugins-pr3-pilot',
                     'version': '1.0.0', 'enabled': True}
        module, fake, original = self.pilot_catalog_fixture((unrelated,))
        desired = module.manifest(LEGACY_SELECTION)
        with self.assertRaisesRegex(ValueError, "unrelated installed plugin"):
            module.bootstrap(self.home, desired, fake, True, retire_pilot_path="/reviewed/local/pilot")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_pilot_source_option_cannot_authorize_another_retired_catalog(self):
        module, fake, _ = self.pilot_catalog_fixture()
        self.config.write_text('[marketplaces.other-retired]\nsource_type = "local"\n'
                               'source = "/reviewed/local/pilot"\n')
        original = self.config.read_bytes()
        desired = module.manifest(LEGACY_SELECTION)
        desired['retire'].append({'plugin_id': 'other-plugin@other-retired', 'version': '1.0.0'})
        with self.assertRaisesRegex(ValueError, "source is unreviewed"):
            module.bootstrap(self.home, desired, fake, True, retire_pilot_path="/reviewed/local/pilot")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.home / ".local/share/agent-plugins").exists())

    def test_home_apply_preserves_local_catalog_and_generated_agent_state(self):
        local_entry = {
            "name": "local-fixture", "source": {"source": "local", "path": "./plugins/local-fixture"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }
        overlay = self.home / ".config/dotfiles/agent-plugins.local.json"
        overlay.parent.mkdir(parents=True)
        overlay.write_text(json.dumps({"plugins": [local_entry]}))
        sentinels = [
            self.home / ".codex/auth.json", self.home / ".codex/sessions/keep",
            self.home / ".codex/plugins/cache/keep", self.home / ".agents/skills/vendor/SKILL.md",
            self.home / ".codex/standard.config.toml", self.home / ".codex/AGENTS.override.md",
            self.home / ".codex/rules/local.rules", self.home / ".codex/memories/keep.md",
            self.home / ".config/dotfiles/agent-plugin-sources.local.json",
        ]
        for p in sentinels:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("KEEP_LOCAL_STATE\n")
        for _ in range(2):
            self.apply_home()
        catalog = json.loads((self.home / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(catalog["plugins"], [local_entry])
        self.assertEqual(catalog["name"], "codex-home-local-marketplace")
        self.assertEqual(self.config.read_bytes(), self.original)
        for p in sentinels:
            self.assertEqual(p.read_text(), "KEEP_LOCAL_STATE\n")
        self.assertEqual(json.loads(overlay.read_text()), {"plugins": [local_entry]})


if __name__ == "__main__":
    unittest.main()
