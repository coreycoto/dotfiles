"""Exercise explicit installation and recovery with local repositories, never live HOME."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/oh-my-zsh.py"
spec = importlib.util.spec_from_file_location("oh_my_zsh_installer", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class OhMyZshTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="dotfiles-omz-test-")
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {
            "HOME": str(self.home), "ZDOTDIR": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_STATE_HOME": str(self.root / "state"),
            "PATH": os.environ["PATH"], "TERM": "dumb", "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        environment = mock.patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.source = self.root / "local upstream"
        self.source.mkdir()
        self.run_command(["git", "init", "--quiet", "--template=", str(self.source)])
        for name in installer.REQUIRED_FILES:
            self.write(self.source / name, "# local installation fixture\n")
        self.write(self.source / "oh-my-zsh.sh", "typeset -g DOTFILES_TEST_OMZ_LOADED=1\n")
        self.write(self.source / "tools/install.sh", '#!/bin/sh\ntouch "$HOME/remote-installer-ran"\n')
        self.write(self.source / ".gitignore", "/custom/\n")
        self.commit_fixture()
        self.pin = {
            "repository": str(self.source),
            "revision": self.run_command(["git", "rev-parse", "HEAD"], cwd=self.source).stdout.strip(),
        }
        self.destination = self.home / ".oh-my-zsh"

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def run_command(self, args, *, cwd=None):
        result = subprocess.run(
            args, cwd=cwd or self.home, env=dict(os.environ),
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def commit_fixture(self):
        self.run_command(["git", "add", "."], cwd=self.source)
        self.run_command([
            "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "commit", "--quiet", "-m", "Local fixture",
        ], cwd=self.source)

    def install(self, *, apply=True, destination=None, pin=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            installer.install(pin or self.pin, destination or self.destination, apply=apply)
        return output.getvalue()

    def apply_dotfiles(self):
        config = self.root / "chezmoi.json"
        config.write_text("{}\n")
        self.run_command([
            shutil.which("chezmoi"), "--source", str(REPO), "--destination", str(self.home),
            "--config", str(config), "--persistent-state", str(self.root / "chezmoi.db"),
            "--cache", str(self.root / "chezmoi-cache"), "--no-pager", "--no-tty",
            "--color=false", "apply", "--force",
        ])

    def test_pin_selects_the_official_repository_and_documented_revision(self):
        pin = installer.load_pin()
        self.assertEqual(pin["repository"], installer.UPSTREAM)
        self.assertRegex(pin["revision"], r"^[0-9a-f]{40}$")
        self.assertIn(pin["revision"], (REPO / "docs/oh-my-zsh.md").read_text())
        for updates in ({"revision": "master"}, {"repository": "https://example.invalid/fork.git"}):
            with self.subTest(updates=updates):
                invalid = dict(pin, **updates)
                with mock.patch.object(Path, "read_text", return_value=json.dumps(invalid)):
                    with self.assertRaises(ValueError):
                        installer.load_pin()

    def test_preview_is_offline_and_does_not_create_parent_directories(self):
        target = self.home / "not created" / "checkout"
        with mock.patch.object(installer, "git", side_effect=AssertionError("preview must be offline")):
            self.assertIn("Preview only", self.install(apply=False, destination=target))
        self.assertFalse(target.parent.exists())
        result = self.run_command([sys.executable, str(SCRIPT)])
        self.assertIn(str(self.destination), result.stdout)
        self.assertFalse(self.destination.exists())
        os.environ["ZSH"] = str(self.home / "local override")
        self.assertIn(os.environ["ZSH"], self.run_command([sys.executable, str(SCRIPT)]).stdout)
        self.assertFalse(Path(os.environ["ZSH"]).exists())

    def test_fresh_install_fetches_exact_detached_commit_without_running_installer_or_hooks(self):
        templates = self.root / "templates"
        self.write(templates / "hooks/post-checkout", '#!/bin/sh\ntouch "$HOME/template-hook-ran"\n')
        (templates / "hooks/post-checkout").chmod(0o755)
        os.environ["GIT_TEMPLATE_DIR"] = str(templates)
        target = self.home / "custom location with spaces"
        self.install(destination=target)
        self.assertEqual(self.run_command(["git", "rev-parse", "HEAD"], cwd=target).stdout.strip(), self.pin["revision"])
        self.assertEqual(self.run_command(["git", "branch", "--show-current"], cwd=target).stdout, "")
        self.assertFalse((target / ".git/hooks/post-checkout").exists())
        self.assertFalse((self.home / "remote-installer-ran").exists())
        self.assertFalse((self.home / "template-hook-ran").exists())
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertEqual(list(target.parent.glob(".dotfiles-oh-my-zsh-*")), [])

    def test_repeated_install_preserves_custom_files_and_performs_no_fetch(self):
        self.install()
        custom = self.destination / "custom/private-theme.zsh-theme"
        self.write(custom, "# authored custom theme\n")
        index = (self.destination / ".git/index").read_bytes()
        original = (self.destination / "oh-my-zsh.sh").stat().st_mtime_ns
        with mock.patch.object(installer, "git", wraps=installer.git) as calls:
            self.assertIn("Already at", self.install())
        self.assertFalse(any("fetch" in call.args for call in calls.call_args_list))
        self.assertEqual(custom.read_text(), "# authored custom theme\n")
        self.assertEqual((self.destination / ".git/index").read_bytes(), index)
        self.assertEqual((self.destination / "oh-my-zsh.sh").stat().st_mtime_ns, original)

    def test_existing_directory_file_and_symlink_are_preserved(self):
        directory = self.home / "existing"
        directory.mkdir()
        self.write(directory / "authored.txt", "keep\n")
        file = self.home / "existing-file"
        file.write_text("keep file\n")
        link = self.home / "linked-installation"
        link.symlink_to(directory, target_is_directory=True)
        for target in (directory, file, link):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.install(destination=target)
        self.assertEqual((directory / "authored.txt").read_text(), "keep\n")
        self.assertEqual(file.read_text(), "keep file\n")
        self.assertTrue(link.is_symlink())

    def test_existing_different_revision_and_tracked_edits_are_preserved(self):
        self.install()
        with self.assertRaisesRegex(ValueError, "different revision"):
            self.install(pin=dict(self.pin, revision="0" * 40))
        entry = self.destination / "oh-my-zsh.sh"
        entry.write_text("# authored tracked customization\n")
        with self.assertRaisesRegex(ValueError, "tracked files have changes"):
            self.install()
        self.assertEqual(entry.read_text(), "# authored tracked customization\n")

    def test_failed_fetch_and_incomplete_checkout_leave_no_installation(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.install(pin=dict(self.pin, revision="0" * 40))
        (self.source / "themes/robbyrussell.zsh-theme").unlink()
        self.commit_fixture()
        revision = self.run_command(["git", "rev-parse", "HEAD"], cwd=self.source).stdout.strip()
        with self.assertRaisesRegex(ValueError, "Missing regular"):
            self.install(pin=dict(self.pin, revision=revision))
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.home.glob(".dotfiles-oh-my-zsh-*")), [])

    def test_relative_and_source_tree_destinations_are_refused(self):
        for destination in (Path("relative"), REPO / ".artifacts/oh-my-zsh"):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                self.install(destination=destination)
        self.assertFalse((REPO / ".artifacts/oh-my-zsh").exists())

    def test_install_and_rollback_keep_shell_options_and_fallback_usable(self):
        self.apply_dotfiles()
        fallback = 'set -e; [[ "$PROMPT" == "%F{green}%~%f %# " ]]; (( ! ${+DOTFILES_TEST_OMZ_LOADED} ))'
        self.run_command(["zsh", "-di", "-c", fallback])
        old_custom = self.home / "existing custom"
        old_custom.mkdir()
        target = self.home / "versioned install"
        options = self.home / ".config/zsh/options.local.zsh"
        local_options = f'ZSH="{target}"\nZSH_CUSTOM="{old_custom}"\nZSH_THEME=local-theme\n'
        options.write_text(local_options)
        self.install(destination=target)
        result = self.run_command(["zsh", "-di", "-c", '''
set -e
[[ "$DOTFILES_TEST_OMZ_LOADED" == 1 && "$ZSH_THEME" == local-theme ]]
[[ "$ZSH_CUSTOM" == "$HOME/existing custom" ]]
[[ "${plugins[*]}" == "git brew" ]]
zstyle -s ':omz:update' mode update_mode
[[ "$update_mode" == disabled ]]
'''])
        self.assertEqual(result.stdout + result.stderr, "")
        self.assertEqual(options.read_text(), local_options)
        target.rename(self.home / "retained recovery tree")
        self.run_command(["zsh", "-di", "-c", fallback])
        self.assertEqual(options.read_text(), local_options)


if __name__ == "__main__":
    unittest.main()
