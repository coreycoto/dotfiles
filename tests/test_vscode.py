"""Bounded editor merges and explicit extension operations in disposable homes."""

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/vscode.py"
SPEC = importlib.util.spec_from_file_location("vscode_preferences", SCRIPT)
VSCODE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VSCODE)


class VSCodeTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="dotfiles-vscode-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.target = self.home / "editor/User/settings.json"
        self.state = self.home / "private-state"
        self.env = os.environ.copy()
        self.env.update(HOME=str(self.home), CFFIXED_USER_HOME=str(self.home))
        self.env.pop("VSCODE_PORTABLE", None)

    def run_helper(self, operation, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), operation,
                                 "--state-dir", str(self.state), *map(str, args)],
                                env=self.env, text=True, capture_output=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def write_settings(self, content):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_bytes(content.encode())

    def receipts(self):
        return sorted(self.state.glob("apply-*/receipt.json"))

    def test_jsonc_merge_preserves_comments_language_blocks_and_unrelated_text(self):
        unrelated = '"[python]": {"editor.tabSize": 4, /* local */ "editor.formatOnSave": false,}'
        original = '{\r\n  // Keep this explanation.\r\n  "git.autofetch": false,\r\n  ' + unrelated + ',\r\n  "local.preference": "a // b /* c */",\r\n}\r\n'
        merged, changed = VSCODE.merge_settings(original, {
            "git.autofetch": True, "diffEditor.renderSideBySide": True,
        })
        self.assertEqual(changed, ["git.autofetch", "diffEditor.renderSideBySide"])
        self.assertIn(unrelated, merged)
        self.assertIn('// Keep this explanation.\r\n', merged)
        self.assertIn('"local.preference": "a // b /* c */"', merged)
        self.assertNotIn("\n", merged.replace("\r\n", ""))
        repeated, changed = VSCODE.merge_settings(merged, {
            "git.autofetch": True, "diffEditor.renderSideBySide": True,
        })
        self.assertEqual(repeated, merged)
        self.assertEqual(changed, [])

    def test_insertion_handles_final_line_comments_nested_arrays_and_empty_objects(self):
        for original in [
            '{"unrelated": [1, {"text": "} , \\\" ",}], // final comment\n}',
            '{"unrelated": true /* final comment */}',
            '{ // only a comment\n}', '{}',
        ]:
            with self.subTest(original=original):
                merged, _ = VSCODE.merge_settings(original, {"selected": True})
                before, _ = VSCODE.jsonc(original)
                after, _ = VSCODE.jsonc(merged)
                self.assertEqual(after, before | {"selected": True})
                if "final comment" in original:
                    self.assertIn("final comment", merged)

    def test_preview_is_read_only_and_does_not_print_setting_values(self):
        self.write_settings('{"unrelated": "synthetic local text"}\n')
        before = self.target.read_bytes()
        result = self.run_helper("settings", "--settings-file", self.target)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(self.state.exists())
        self.assertNotIn("synthetic local text", result.stdout + result.stderr)

    def test_apply_backs_up_original_privately_merges_local_override_and_repeats(self):
        original = '{\n  // authored locally\n  "local.preference": {"keep": true},\n  "git.autofetch": false\n}\n'
        self.write_settings(original)
        self.target.chmod(0o640)
        overlay = self.home / ".config/dotfiles/vscode/settings.local.json"
        overlay.parent.mkdir(parents=True)
        overlay.write_text('{"git.autofetch": false, "terminal.integrated.fontSize": 14}\n')
        self.run_helper("settings", "--settings-file", self.target, "--apply")
        merged = self.target.read_bytes()
        data, _ = VSCODE.jsonc(merged.decode())
        self.assertFalse(data["git.autofetch"])
        self.assertEqual(data["terminal.integrated.fontSize"], 14)
        self.assertEqual(data["local.preference"], {"keep": True})
        self.assertIn(b"// authored locally", merged)
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)
        receipt_path, = self.receipts()
        receipt = json.loads(receipt_path.read_text())
        backup = receipt_path.parent / "settings.before.json"
        self.assertEqual(backup.read_text(), original)
        self.assertEqual(receipt["status"], "applied")
        self.assertTrue(receipt["existed"])
        self.assertEqual(stat.S_IMODE(receipt_path.parent.stat().st_mode), 0o700)
        for path in (receipt_path, backup):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.run_helper("settings", "--settings-file", self.target, "--apply")
        self.assertEqual(self.target.read_bytes(), merged)
        self.assertEqual(len(self.receipts()), 1)
        self.assertEqual(json.loads(overlay.read_text())["terminal.integrated.fontSize"], 14)

    def test_new_profile_settings_are_private_and_preview_creates_nothing(self):
        self.run_helper("settings", "--settings-file", self.target)
        self.assertFalse(self.target.parent.exists())
        self.run_helper("settings", "--settings-file", self.target, "--apply")
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)
        receipt = json.loads(self.receipts()[0].read_text())
        self.assertFalse(receipt["existed"])
        self.assertFalse((self.receipts()[0].parent / "settings.before.json").exists())

    def test_malformed_duplicate_or_nonobject_settings_fail_before_mutation(self):
        for original in [
            '{"selected": true, "selected": false}',
            '{"nested": {"duplicate": 1, "duplicate": 2}}',
            '{"broken": }', '{"value": NaN}', '[]', '{ /* unclosed',
            '{,}', '{"invalid": [,]}', '{"invalid":,}',
        ]:
            with self.subTest(original=original):
                self.write_settings(original)
                self.run_helper("settings", "--settings-file", self.target, "--apply", success=False)
                self.assertEqual(self.target.read_text(), original)
                self.assertFalse(self.state.exists())

    def test_symlink_and_repo_destinations_are_rejected_without_writing(self):
        self.target.parent.mkdir(parents=True)
        elsewhere = self.home / "shared.json"
        elsewhere.write_text("{}\n")
        self.target.symlink_to(elsewhere)
        self.run_helper("settings", "--settings-file", self.target, "--apply", success=False)
        self.assertEqual(elsewhere.read_text(), "{}\n")
        self.run_helper("settings", "--settings-file", REPO / "home/settings.json", "--apply", success=False)
        self.assertFalse(self.state.exists())

    def test_settings_reject_profile_selector_instead_of_editing_default_profile(self):
        self.run_helper("settings", "--settings-file", self.target, "--profile", "Other", "--apply", success=False)
        self.assertFalse(self.target.exists())

    def test_missing_explicit_overlay_stops_before_applying_portable_values(self):
        self.write_settings('{"git.autofetch": false}\n')
        before = self.target.read_bytes()
        self.run_helper("settings", "--settings-file", self.target,
                        "--local-settings", self.home / "missing-overlay.json", "--apply", success=False)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(self.state.exists())

    def fake_code(self, before):
        inventory = self.root / "extension-inventory.json"
        inventory.write_text(json.dumps(before))
        calls = self.root / "calls.jsonl"
        self.env.update(DOTFILES_TEST_INVENTORY=str(inventory), DOTFILES_TEST_CALLS=str(calls))
        code = self.root / "fake code"
        code.write_text('''#!''' + sys.executable + '''
import json, os, pathlib, sys
args = sys.argv[1:]
inventory = pathlib.Path(os.environ["DOTFILES_TEST_INVENTORY"])
calls = pathlib.Path(os.environ["DOTFILES_TEST_CALLS"])
with calls.open("a") as stream: stream.write(json.dumps(args) + "\\n")
if os.environ.get("VSCODE_IPC_HOOK_CLI") or os.environ.get("VSCODE_EXTENSIONS"):
    sys.exit(71)
if "--version" in args:
    print(os.environ.get("DOTFILES_TEST_CODE_VERSION", "1.140.0"))
elif "--list-extensions" in args:
    for name, version in json.loads(inventory.read_text()).items(): print(name + "@" + version)
elif "--install-extension" in args:
    name, version = args[args.index("--install-extension") + 1].split("@")
    if name == os.environ.get("DOTFILES_TEST_FAIL_EXTENSION"):
        print("synthetic private diagnostic", file=sys.stderr)
        sys.exit(70)
    data = json.loads(inventory.read_text())
    data[name] = version
    if os.environ.get("DOTFILES_TEST_CHANGE_UNRELATED"): data["example.unrelated"] = "9.9.9"
    inventory.write_text(json.dumps(data))
''')
        code.chmod(0o755)
        return code, inventory, calls

    def test_extension_preview_runs_no_commands_and_creates_no_state(self):
        code, inventory, calls = self.fake_code({"example.unrelated": "1.2.3"})
        result = self.run_helper("extensions", "--code", code)
        self.assertIn("ms-python.debugpy@", result.stdout)
        self.assertFalse(calls.exists())
        self.assertFalse(self.state.exists())
        self.assertEqual(json.loads(inventory.read_text()), {"example.unrelated": "1.2.3"})

    def test_extension_apply_is_pinned_preserves_unrelated_and_skips_repeated_installs(self):
        selected = VSCODE.extension_selection()
        code, inventory, calls = self.fake_code({
            "example.unrelated": "1.2.3", "ms-python.python": "2025.1.0",
            "ms-python.debugpy": selected["ms-python.debugpy"],
        })
        self.env.update(VSCODE_IPC_HOOK_CLI="synthetic remote socket", VSCODE_EXTENSIONS="synthetic wrong directory")
        selectors = ["--code", code, "--user-data-dir", self.home / "editor",
                     "--extensions-dir", self.home / "extensions", "--profile", "Existing Profile", "--apply"]
        self.run_helper("extensions", *selectors)
        self.assertEqual(json.loads(inventory.read_text()), selected | {"example.unrelated": "1.2.3"})
        first = [json.loads(line) for line in calls.read_text().splitlines()]
        installs = [command for command in first if "--install-extension" in command]
        self.assertEqual(len(installs), len(selected) - 1)
        for command in installs:
            self.assertIn("--force", command)
            self.assertIn("--do-not-sync", command)
            self.assertIn("--do-not-include-pack-dependencies", command)
            self.assertEqual(command[command.index("--profile") + 1], "Existing Profile")
            self.assertNotIn("--update-extensions", command)
            self.assertNotIn("--uninstall-extension", command)
        self.run_helper("extensions", *selectors)
        all_calls = [json.loads(line) for line in calls.read_text().splitlines()]
        self.assertEqual(sum("--install-extension" in command for command in all_calls), len(installs))
        self.assertTrue(all(json.loads(path.read_text())["status"] == "applied" for path in self.receipts()))

    def test_partial_extension_failure_retains_receipt_and_does_not_retry(self):
        code, inventory, calls = self.fake_code({"example.unrelated": "1.2.3"})
        self.env["DOTFILES_TEST_FAIL_EXTENSION"] = "biomejs.biome"
        result = self.run_helper("extensions", "--code", code, "--apply", success=False)
        receipt = json.loads(self.receipts()[0].read_text())
        self.assertEqual(receipt["status"], "incomplete")
        self.assertEqual(receipt["completed"], ["astral-sh.ty"])
        commands = [json.loads(line) for line in calls.read_text().splitlines()]
        self.assertEqual(sum("--install-extension" in command for command in commands), 2)
        self.assertNotIn("synthetic private diagnostic", result.stdout + result.stderr)
        self.assertEqual(json.loads(inventory.read_text())["example.unrelated"], "1.2.3")

    def test_unrelated_extension_change_is_reported_as_incomplete(self):
        code, _, _ = self.fake_code({"example.unrelated": "1.2.3"})
        self.env["DOTFILES_TEST_CHANGE_UNRELATED"] = "1"
        self.run_helper("extensions", "--code", code, "--apply", success=False)
        self.assertEqual(json.loads(self.receipts()[0].read_text())["status"], "incomplete")

    def test_incompatible_code_and_portable_mode_fail_before_installation(self):
        code, inventory, calls = self.fake_code({})
        self.env["DOTFILES_TEST_CODE_VERSION"] = "1.99.0"
        self.run_helper("extensions", "--code", code, "--apply", success=False)
        commands = [json.loads(line) for line in calls.read_text().splitlines()]
        self.assertFalse(any("--install-extension" in command for command in commands))
        self.assertEqual(json.loads(inventory.read_text()), {})
        calls.unlink()
        self.env["VSCODE_PORTABLE"] = str(self.home / "portable-data")
        self.run_helper("extensions", "--code", code, "--apply", success=False)
        self.assertFalse(calls.exists())


if __name__ == "__main__":
    unittest.main()
