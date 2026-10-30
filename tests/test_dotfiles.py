"""Exercise installation, shell behavior, recovery, and the credential boundary."""

import json
import fcntl
import os
from pathlib import Path
import platform
import pty
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import tomllib
import unittest

from terminal_harness import isolated_terminal_test


REPO = Path(__file__).resolve().parents[1]
FILES = json.loads((REPO / "manifest.json").read_text())["files"]


def brew_updates(*names):
    return json.dumps({"formulae": [
        {"name": name, "installed_versions": ["1.0.0"], "current_version": "2.0.0", "pinned": False}
        for name in names
    ], "casks": []})


class TerminalSession:
    """Exercise ZLE through an owned controlling terminal, without a GUI app."""

    def __init__(self, home, env):
        self.output = b""
        zsh = shutil.which("zsh")
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(home)
            os.execve(zsh, [zsh, "-di"], {**env, "TERM": "xterm-256color", "LC_ALL": "en_US.UTF-8"})
        sys.stderr.write(f"PTY shell pid={self.pid}\n")
        sys.stderr.flush()
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 100, 0, 0))

    def read_for(self, duration):
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            if select.select([self.fd], [], [], max(0, min(0.05, deadline - time.monotonic())))[0]:
                chunk = os.read(self.fd, 65536)
                self.output += chunk
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()

    def until(self, text, timeout=5):
        deadline = time.monotonic() + timeout
        while text.encode() not in self.output and time.monotonic() < deadline:
            self.read_for(0.05)
        if text.encode() not in self.output:
            raise AssertionError(f"Terminal did not show {text!r}: {self.output!r}")

    def send(self, text):
        os.write(self.fd, text.encode())

    def close(self):
        if os.waitpid(self.pid, os.WNOHANG)[0] == 0:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        os.close(self.fd)


class DotfilesTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="dotfiles-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.test_home = self.root / "home"
        self.test_home.mkdir()
        self.state = self.root / "state"
        self.state.mkdir()
        self.config = self.state / "chezmoi.json"
        self.config.write_text("{}\n")
        self.env = {
            "HOME": str(self.test_home),
            "ZDOTDIR": str(self.test_home),
            "XDG_CONFIG_HOME": str(self.test_home / ".config"),
            "XDG_CACHE_HOME": str(self.state / "cache"),
            "XDG_DATA_HOME": str(self.state / "data"),
            "XDG_STATE_HOME": str(self.state / "state"),
            "PATH": os.environ["PATH"],
            "TERM": "dumb",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        self.chezmoi = [
            shutil.which("chezmoi"),
            "--source", str(REPO),
            "--destination", str(self.test_home),
            "--config", str(self.config),
            "--persistent-state", str(self.state / "chezmoi.db"),
            "--cache", str(self.state / "chezmoi-cache"),
            "--no-pager", "--no-tty", "--color=false",
        ]

    def run_command(self, args, *, cwd=None, check=True):
        result = subprocess.run(
            args, cwd=cwd or self.test_home, env=self.env,
            text=True, capture_output=True, timeout=30,
        )
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def install(self):
        self.run_command(self.chezmoi + ["apply", "--force"])

    def write(self, path, text, executable=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if executable:
            path.chmod(0o755)
        return path

    def shell(self, code, flags="-df"):
        return self.run_command([shutil.which("zsh"), flags, "-c", code])

    def test_manifest_matches_actual_chezmoi_targets(self):
        targets = [entry["target"] for entry in FILES]
        sources = [entry["source"] for entry in FILES]
        self.assertEqual(len(targets), len(set(targets)))
        self.assertEqual(len(sources), len(set(sources)))
        declared = set(sources)
        actual = {
            str(path.relative_to(REPO))
            for path in (REPO / "home").rglob("*")
            if path.is_file() and path.name != ".chezmoiignore"
        }
        self.assertEqual(actual, declared)
        for target in targets:
            path = Path(target)
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
        managed = self.run_command(self.chezmoi + ["managed", "--include=files", "--path-style=relative"])
        self.assertEqual(set(managed.stdout.splitlines()), set(targets))

    def test_repeated_apply_preserves_unmanaged_files(self):
        sentinels = [
            ".gitconfig.local", ".config/zsh/local.zsh",
            ".config/zsh/options.local.zsh", ".aws/credentials",
            ".agents/skills/unrelated/SKILL.md",
            ".codex/rules/default.rules", ".codex/rules/coreycoto.com.rules",
            ".codex/rules/unrelated.rules", ".codex/config.toml",
            ".codex/rules/personal.rules", ".codex/rules/legacy-project.rules",
            ".codex/hooks.json",
            ".config/dotfiles/bun-globals.json", ".local/bin/dotfiles-bun-globals",
            ".config/dotfiles/vscode/settings.local.json",
            "Library/Application Support/Code/User/settings.json",
            "Library/Application Support/Code/User/keybindings.json",
            "Library/Application Support/Code/User/globalStorage/state.vscdb",
            ".vscode/argv.json", ".vscode/extensions/unrelated/sentinel",
        ]
        for target in sentinels:
            self.write(self.test_home / target, "# unmanaged sentinel\n")
        self.install()
        first = {entry["target"]: (self.test_home / entry["target"]).read_bytes() for entry in FILES}
        self.install()
        self.assertEqual(
            first,
            {entry["target"]: (self.test_home / entry["target"]).read_bytes() for entry in FILES},
        )
        self.assertEqual(self.run_command(self.chezmoi + ["status"]).stdout, "")
        self.run_command(self.chezmoi + ["verify"])
        for target in sentinels:
            self.assertEqual((self.test_home / target).read_text(), "# unmanaged sentinel\n")
        self.assertFalse((self.test_home / "README.md").exists())
        self.assertFalse((self.test_home / "Brewfile").exists())

    def ssh_options(self, host):
        result = self.run_command([
            shutil.which("ssh"), "-G", "-F", str(self.test_home / ".ssh/config"),
            "-o", "CanonicalizeHostname=no", host,
        ])
        return dict(line.split(" ", 1) for line in result.stdout.splitlines())

    def test_ssh_defaults_and_private_permissions_without_overlay(self):
        self.install()
        self.assertEqual((self.test_home / ".ssh").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.test_home / ".ssh/config").stat().st_mode & 0o777, 0o600)
        options = self.ssh_options("ssh-example.invalid")
        self.assertEqual(options["stricthostkeychecking"], "ask")
        self.assertEqual(options["forwardagent"], "no")
        self.assertEqual(options["identitiesonly"], "no")
        self.assertNotIn("identityagent", options)
        self.assertFalse((self.test_home / ".ssh/config.local").exists())

    def test_ssh_local_identity_and_agent_selection_survive_repeated_apply(self):
        old_home = self.test_home
        self.test_home = self.root / "home with spaces"
        old_home.rename(self.test_home)
        for key in ["HOME", "ZDOTDIR"]:
            self.env[key] = str(self.test_home)
        self.env["XDG_CONFIG_HOME"] = str(self.test_home / ".config")
        self.chezmoi[self.chezmoi.index("--destination") + 1] = str(self.test_home)
        overlay = self.write(self.test_home / ".ssh/config.local", """
Host ssh-example
    HostName ssh.example.invalid
    User example-user
    IdentityAgent /tmp/dotfiles-synthetic-agent.sock
    IdentityFile ~/.ssh/example-key.pub
    IdentitiesOnly yes
    StrictHostKeyChecking yes
""")
        overlay.chmod(0o600)
        sentinels = [self.write(self.test_home / ".ssh" / name, "synthetic sentinel\n")
                     for name in ["example-key.pub", "local-key", "known_hosts"]]
        self.install()
        first = (self.test_home / ".ssh/config").read_bytes()
        self.install()
        self.assertEqual((self.test_home / ".ssh/config").read_bytes(), first)
        options = self.ssh_options("ssh-example")
        self.assertEqual(options["hostname"], "ssh.example.invalid")
        self.assertEqual(options["user"], "example-user")
        self.assertEqual(options["identityagent"], "/tmp/dotfiles-synthetic-agent.sock")
        self.assertEqual(options["identityfile"], "~/.ssh/example-key.pub")
        self.assertEqual(options["identitiesonly"], "yes")
        self.assertEqual(options["stricthostkeychecking"], "true")
        self.assertEqual(options["forwardagent"], "no")
        unrelated = self.ssh_options("other-example.invalid")
        self.assertEqual(unrelated["stricthostkeychecking"], "ask")
        self.assertNotIn("identityagent", unrelated)
        self.assertEqual(overlay.stat().st_mode & 0o777, 0o600)
        self.assertIn("Host ssh-example", overlay.read_text())
        for path in sentinels:
            self.assertEqual(path.read_text(), "synthetic sentinel\n")
        self.run_command(self.chezmoi + ["verify"])

    def test_zsh_syntax(self):
        sources = [entry["source"] for entry in FILES if entry["source"].endswith(".zsh")]
        sources += ["home/dot_zprofile", "home/dot_zshrc"]
        for source in sources:
            with self.subTest(source=source):
                self.run_command([shutil.which("zsh"), "-n", str(REPO / source)])

    def command_spies(self):
        self.env["DOTFILES_TEST_COMMAND_LOG"] = str(self.root / "command-log")
        for command in ["brew", "bun", "vercel", "mise", "curl"]:
            self.write(
                self.test_home / ".local/bin" / command,
                '#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$DOTFILES_TEST_COMMAND_LOG"\nprintf "1.2.3\\n"\n',
                executable=True,
            )

    def test_fresh_interactive_shell_is_quiet_and_does_no_tool_checks(self):
        self.install()
        self.command_spies()
        self.write(self.test_home / ".bun/_bun", "DOTFILES_TEST_COMPLETION_SOURCED=1\n")
        result = self.shell('[[ "$DOTFILES_TEST_COMPLETION_SOURCED" == 1 ]]', flags="-di")
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertFalse((self.root / "command-log").exists())

    def test_login_noninteractive_shell_loads_paths_but_not_diagnostics(self):
        self.install()
        self.command_spies()
        result = self.shell('print -r -- "$path[1]"; (( ! $+functions[tool-status] ))', flags="-dl")
        self.assertEqual(result.stdout.strip(), str(self.test_home / ".local/bin"))
        self.assertEqual(result.stderr, "")
        self.assertFalse((self.root / "command-log").exists())

    def mise_node_fixture(self):
        # Real mise dispatch, with disposable fake runtimes; no downloads.
        # This scenario installs only runtimes, not the independent global CLIs.
        config = self.test_home / ".config/mise/config.toml"
        text = config.read_text()
        start = text.index("# Global CLI updates")
        end = text.index("[settings]", start)
        config.write_text(text[:start] + text[end:])
        self.env["MISE_OFFLINE"] = "1"
        self.env["MISE_DATA_DIR"] = str(self.state / "data/mise")
        self.env["MISE_CACHE_DIR"] = str(self.state / "mise-cache")
        self.env["MISE_CONFIG_DIR"] = str(self.test_home / ".config/mise")
        for version in ("24.21.0", "22.23.3"):
            runtime = self.root / "runtimes" / version
            self.write(runtime / "bin/node", f"#!/bin/sh\nprintf 'v{version}\\n'\n", executable=True)
            self.run_command([shutil.which("mise"), "link", f"node@{version}", str(runtime)])
        self.run_command([shutil.which("mise"), "reshim"])

    def test_mise_selects_project_runtime_and_project_bins_still_win(self):
        self.install()
        self.mise_node_fixture()
        project = self.root / "Project [runtime] with spaces"
        self.write(project / "mise.local.toml", '[tools]\nnode = "22.23.3"\n')
        self.env["DOTFILES_TEST_PROJECT"] = str(project)
        result = self.shell('''
node --version
cd "$DOTFILES_TEST_PROJECT"
node --version
cd "$HOME"
node --version
source "$HOME/.zshrc"
node --version
''', flags="-di")
        self.assertEqual(result.stdout.splitlines(), ["v24.21.0", "v22.23.3", "v24.21.0", "v24.21.0"])
        self.assertEqual(result.stderr, "")
        self.write(project / "node_modules/.bin/node", "#!/bin/sh\nprintf 'project-cli\\n'\n", executable=True)
        result = self.shell('cd "$DOTFILES_TEST_PROJECT"; node --version; cd "$HOME"; node --version', flags="-di")
        self.assertEqual(result.stdout.splitlines(), ["project-cli", "v24.21.0"])

    def test_missing_project_runtime_fails_without_installing_or_falling_back(self):
        self.install()
        self.mise_node_fixture()
        project = self.root / "missing-runtime"
        self.write(project / "mise.local.toml", '[tools]\nnode = "99.99.99"\n')
        before = sorted(str(path) for path in (self.state / "data/mise/installs/node").iterdir())
        result = self.run_command([shutil.which("zsh"), "-di", "-c", "node --version"], cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("99.99.99", result.stderr)
        self.assertEqual(before, sorted(str(path) for path in (self.state / "data/mise/installs/node").iterdir()))

    def test_global_bun_stays_in_major_one_and_project_exact_pin_wins(self):
        self.install()
        self.mise_node_fixture()
        for version in ("1.3.14", "1.4.2", "2.0.0"):
            runtime = self.root / "runtimes/bun" / version
            self.write(runtime / "bin/bun", f"#!/bin/sh\nprintf '{version}\\n'\n", executable=True)
            self.run_command([shutil.which("mise"), "link", f"bun@{version}", str(runtime)])
        self.run_command([shutil.which("mise"), "reshim"])
        project = self.root / "pinned-bun-project"
        selector = self.write(project / "mise.local.toml", '[tools]\nbun = "1.3.14"\n')
        before = selector.read_bytes()
        self.env["DOTFILES_TEST_PROJECT"] = str(project)
        result = self.shell('''
bun --version
cd "$DOTFILES_TEST_PROJECT"
bun --version
cd "$HOME"
bun --version
''', flags="-di")
        self.assertEqual(result.stdout.splitlines(), ["1.4.2", "1.3.14", "1.4.2"])
        self.assertEqual(result.stderr, "")
        self.assertEqual(selector.read_bytes(), before)

    def project_tools(self, project, *tools, apply=False, check=True):
        args = [shutil.which("python3"), str(REPO / "scripts/project-tools.py"), "--project", str(project)]
        for tool in tools:
            args += ["--tool", tool]
        if apply:
            args += ["--apply"]
        return self.run_command(args, check=check)

    def test_project_selector_preview_then_apply_preserves_source_and_ignore_rules(self):
        project = self.root / "Project *local*"
        project.mkdir()
        self.run_command([shutil.which("git"), "init", "--quiet", str(project)])
        self.write(project / "mise.toml", '[tools]\ntuist = "4.201.0"\n')
        self.run_command([shutil.which("git"), "add", "mise.toml"], cwd=project)
        exclude = project / ".git/info/exclude"
        exclude.write_text("# keep this\n/existing-private-file")
        original_source = (project / "mise.toml").read_bytes()
        original_status = self.run_command([shutil.which("git"), "status", "--porcelain"], cwd=project).stdout
        self.project_tools(project, "node@24.21.0", "bun@1.3.14")
        self.assertFalse((project / "mise.local.toml").exists())
        self.assertEqual(exclude.read_text(), "# keep this\n/existing-private-file")
        self.project_tools(project, "node@24.21.0", "bun@1.3.14", apply=True)
        self.project_tools(project, "node@24.21.0", "bun@1.3.14", apply=True)
        self.assertEqual(exclude.read_text(), "# keep this\n/existing-private-file\n/mise.local.toml\n")
        self.assertEqual((project / "mise.toml").read_bytes(), original_source)
        self.assertEqual(self.run_command([shutil.which("git"), "status", "--porcelain"], cwd=project).stdout, original_status)
        self.assertEqual((project / "mise.local.toml").stat().st_mode & 0o777, 0o600)
        self.assertEqual(tomllib.loads((project / "mise.local.toml").read_text())["tools"], {"bun": "1.3.14", "node": "24.21.0"})

    def test_project_selector_rejects_ranges_conflicts_tracked_files_and_symlinks(self):
        project = self.root / "guarded-project"
        project.mkdir()
        self.run_command([shutil.which("git"), "init", "--quiet", str(project)])
        exclude = project / ".git/info/exclude"
        original_exclude = exclude.read_bytes()
        for spec in ("node@24", "node@latest", "node@^24.0.0", "npm:unreviewed@1.0.0"):
            self.assertEqual(self.project_tools(project, spec, apply=True, check=False).returncode, 2)
        target = self.write(project / "mise.local.toml", '# private settings\n[env]\nEDITOR = "vim"\n')
        original = target.read_bytes()
        self.assertEqual(self.project_tools(project, "node@24.21.0", apply=True, check=False).returncode, 2)
        self.assertEqual(target.read_bytes(), original)
        target.unlink()
        target.symlink_to(project / "another-file")
        self.assertEqual(self.project_tools(project, "node@24.21.0", apply=True, check=False).returncode, 2)
        target.unlink()
        self.project_tools(project, "node@24.21.0", apply=True)
        self.run_command([shutil.which("git"), "add", "--force", "mise.local.toml"], cwd=project)
        current_exclude = exclude.read_bytes()
        self.assertEqual(self.project_tools(project, "node@24.21.0", apply=True, check=False).returncode, 2)
        self.assertEqual(exclude.read_bytes(), current_exclude)
        self.assertTrue(current_exclude.startswith(original_exclude))

    def test_mise_installation_preview_does_not_run_tools_or_change_requests(self):
        self.command_spies()
        source = REPO / "home/dot_config/mise/config.toml"
        before = source.read_bytes()
        preview = self.run_command([shutil.which("python3"), str(REPO / "scripts/mise-tools.py")])
        self.assertIn(" install ", preview.stdout)
        self.assertIn("github:coreycoto/git-slop", preview.stdout)
        self.assertFalse((self.root / "command-log").exists())
        self.assertEqual(source.read_bytes(), before)

    def test_installed_tool_updater_uses_mise_without_retired_bun_targets(self):
        self.install()
        self.assertFalse((self.test_home / ".config/dotfiles/bun-globals.json").exists())
        self.assertFalse((self.test_home / ".local/bin/dotfiles-bun-globals").exists())
        self.status_spies()
        source = REPO / "home/dot_config/mise/config.toml"
        installed = self.test_home / ".config/mise/config.toml"
        before_source, before_installed = source.read_bytes(), installed.read_bytes()
        result = self.shell("dotfiles update --dry-run", flags="-di")
        self.assertIn("upgrade --global --dry-run", result.stdout)
        self.assertIn("npm:neon", result.stdout)
        self.assertIn("github:coreycoto/git-slop", result.stdout)
        calls = (self.root / "command-log").read_text()
        self.assertNotIn("bun add", calls)
        self.assertNotIn(" install ", calls)
        self.assertEqual(source.read_bytes(), before_source)
        self.assertEqual(installed.read_bytes(), before_installed)

    def test_installed_dotfiles_cli_shows_help_and_previews_upgrades(self):
        self.install()
        self.status_spies()
        self.env["PATH"] = str(self.test_home / ".local/bin") + os.pathsep + self.env["PATH"]
        launcher = self.test_home / ".local/bin/dotfiles"
        self.assertFalse((self.test_home / ".local/bin/dotfiles-tools").exists())
        help_result = self.run_command([str(launcher), "--help"], cwd=self.root)
        self.assertIn("update", help_result.stdout)
        result = self.run_command([str(launcher), "update", "--dry-run"], cwd=self.root)
        self.assertIn("upgrade --global --dry-run", result.stdout)
        self.assertIn("npm:neon", result.stdout)
        self.assertIn("mise --cd ", (self.root / "command-log").read_text())

    def test_gh_steward_extension_forwards_arguments_and_exit_status_to_mise(self):
        self.install()
        self.command_spies()
        self.env["PATH"] = str(self.test_home / ".local/bin") + ":" + self.env["PATH"]
        self.write(self.test_home / ".local/bin/mise", '#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/extension-args"\nexit 7\n', executable=True)
        wrapper = self.test_home / ".local/share/dotfiles/gh-steward/gh-steward"
        result = self.run_command([str(wrapper), "version", "--json", "argument with spaces"], check=False)
        self.assertEqual(result.returncode, 7)
        self.assertEqual((self.test_home / "extension-args").read_text().splitlines(),
                         ["exec", "--", "gh-steward", "version", "--json", "argument with spaces"])

    def test_uv_skips_its_interpreter_cache_when_using_path_python(self):
        self.install()
        self.env["UV_PYTHON_INSTALL_DIR"] = str(self.root / "uv-python")
        version = platform.python_version()
        system = {"Darwin": "macos", "Linux": "linux"}[platform.system()]
        architecture = {"arm64": "aarch64"}.get(platform.machine(), platform.machine())
        minor = ".".join(version.split(".")[:2])
        marker = self.root / "managed-python-invoked"
        managed = Path(self.env["UV_PYTHON_INSTALL_DIR"]) / f"cpython-{version}-{system}-{architecture}-none" / "bin" / f"python{minor}"
        self.write(managed, "#!/bin/sh\ntouch " + shlex.quote(str(marker)) + "\nexec " + shlex.quote(sys.executable) + ' "$@"\n', executable=True)
        (managed.parent / "python3").symlink_to(managed.name)
        (managed.parent / "python").symlink_to(managed.name)
        args = [shutil.which("uv"), "python", "find", "--no-project", "--offline", "--no-cache"]
        # The cache candidate forwards to the real test interpreter. Establish
        # that preferring uv installations probes it before the PATH runtime.
        self.env["UV_PYTHON_PREFERENCE"] = "managed"
        control = self.run_command(args)
        self.assertTrue(Path(control.stdout.strip()).is_file())
        self.assertTrue(marker.exists())
        marker.unlink()
        self.env.pop("UV_PYTHON_PREFERENCE")
        selection = self.run_command(args)
        self.assertFalse(selection.stdout.strip().startswith(self.env["UV_PYTHON_INSTALL_DIR"]))
        self.assertTrue(Path(selection.stdout.strip()).is_file())
        self.assertFalse(marker.exists())

    def test_machine_options_load_before_plugins_and_final_overrides_after(self):
        self.install()
        self.write(self.test_home / ".config/zsh/options.local.zsh", "ZSH_THEME=local-theme\nDOTFILES_ENABLE_DOTENV=1\n")
        self.write(self.test_home / ".oh-my-zsh/oh-my-zsh.sh", 'print -r -- "$ZSH_THEME ${plugins[*]}"\n')
        self.write(self.test_home / ".config/zsh/local.zsh", "print -r -- final-override\n")
        result = self.shell(":", flags="-di")
        self.assertEqual(result.stdout.splitlines(), ["local-theme git brew dotenv", "final-override"])

    def test_oh_my_zsh_updates_and_dotenv_are_disabled_by_default(self):
        self.install()
        self.write(
            self.test_home / ".oh-my-zsh/oh-my-zsh.sh",
            'zstyle -s ":omz:update" mode update_mode\nprint -r -- "$update_mode ${plugins[*]}"\n',
        )
        self.assertEqual(self.shell(":", flags="-di").stdout.strip(), "disabled git brew")

    def test_changing_projects_removes_old_bins_and_preserves_global_command(self):
        self.install()
        first = self.root / "Project [one] with spaces"
        second = self.root / "Project *two*"
        for folder, label in [(first / "node_modules/.bin", "first-node"), (first / "bin", "first-bin"), (second / ".bin", "second"), (self.test_home / ".local/bin", "global")]:
            self.write(folder / "dotfiles-probe", f"#!/bin/sh\nprintf '{label}\\n'\n", executable=True)
        self.env["DOTFILES_TEST_FIRST"] = str(first)
        self.env["DOTFILES_TEST_SECOND"] = str(second)
        result = self.shell('''
source "$HOME/.config/zsh/environment.zsh"
source "$HOME/.config/zsh/project-bins.zsh"
cd "$DOTFILES_TEST_FIRST"
dotfiles-probe
cd "$DOTFILES_TEST_SECOND"
dotfiles-probe
for entry in "${path[@]}"; do
  [[ "$entry" == "$DOTFILES_TEST_FIRST/"* ]] && exit 10
done
cd "$HOME"
dotfiles-probe
for entry in "${path[@]}"; do
  [[ "$entry" == "$DOTFILES_TEST_SECOND/"* ]] && exit 11
done
true
''')
        self.assertEqual(result.stdout.splitlines(), ["first-node", "second", "global"])

    def test_resourcing_shell_does_not_duplicate_paths_or_hooks(self):
        self.install()
        (self.test_home / ".local/bin").mkdir(parents=True, exist_ok=True)
        result = self.shell('''
source "$HOME/.zshrc"
source "$HOME/.zshrc"
print -l -- "${path[@]}"
print -- --hooks--
print -l -- "${chpwd_functions[@]}"
''', flags="-di")
        paths, hooks = result.stdout.split("--hooks--\n")
        self.assertEqual(len(paths.splitlines()), len(set(paths.splitlines())))
        self.assertEqual(hooks.splitlines().count("refresh_project_bins"), 1)

    def test_shim_updater_dispatches_through_official_mise_entry_point(self):
        self.install()
        mise = self.write(self.test_home / ".local/bin/mise", '''#!/bin/sh
case "$0" in
  */mise) printf 'updater:%s\\n' "$*" ;;
  *) exec "$__MISE_BIN" __tool-update --id fixture ;;
esac
''', executable=True)
        shims = self.state / "data/mise/shims"
        shims.mkdir(parents=True)
        (shims / "fixture-tool").symlink_to(mise)
        self.env["__MISE_BIN"] = "/missing/old-mise"
        result = self.shell('source "$HOME/.config/zsh/environment.zsh"; fixture-tool')
        self.assertEqual(result.stdout.strip(), "updater:__tool-update --id fixture")

    def test_posix_profile_is_idempotent(self):
        self.install()
        (self.test_home / ".local/bin").mkdir(parents=True, exist_ok=True)
        result = self.run_command(["/bin/sh", "-c", '. "$HOME/.profile"; . "$HOME/.profile"; printf "%s\\n" "$PATH"'])
        self.assertEqual(result.stdout.strip().split(":").count(str(self.test_home / ".local/bin")), 1)

    def test_login_profiles_keep_docker_cli_available_without_duplicates(self):
        old_home = self.test_home
        self.test_home = self.root / "home with spaces"
        old_home.rename(self.test_home)
        for key in ["HOME", "ZDOTDIR"]:
            self.env[key] = str(self.test_home)
        self.env["XDG_CONFIG_HOME"] = str(self.test_home / ".config")
        self.chezmoi[self.chezmoi.index("--destination") + 1] = str(self.test_home)
        docker_bin = self.test_home / ".docker/bin"
        cli = self.write(docker_bin / "dotfiles-docker-fixture", "#!/bin/sh\nprintf 'docker-cli-available\\n'\n", executable=True)
        self.install()
        self.install()
        self.assertEqual(cli.read_text(), "#!/bin/sh\nprintf 'docker-cli-available\\n'\n")
        self.assertEqual(self.run_command(self.chezmoi + ["status"]).stdout, "")
        inherited = [str(self.test_home / "other bin"), "/usr/bin", "/bin"]
        for shell, profile, flags in [("/bin/sh", ".profile", []), (shutil.which("zsh"), ".zprofile", ["-df"])]:
            for already_present in [False, True]:
                with self.subTest(profile=profile, already_present=already_present):
                    entries = inherited.copy()
                    if already_present:
                        entries.insert(2, str(docker_bin))
                    self.env["PATH"] = ":".join(entries)
                    source = f'. "$HOME/{profile}"; '
                    result = self.run_command([shell, *flags, "-c", source * 2 + 'printf "%s\\n" "$PATH"; dotfiles-docker-fixture'])
                    path, output = result.stdout.splitlines()
                    paths = path.split(":")
                    self.assertEqual(output, "docker-cli-available")
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(paths.count(str(docker_bin)), 1)
                    self.assertEqual([p for p in paths if p in entries], entries)
                    if not already_present:
                        self.assertEqual(paths[-1], str(docker_bin))

    def test_login_profiles_do_not_add_a_missing_docker_directory(self):
        self.install()
        self.env["PATH"] = "/usr/bin:/bin"
        for shell, profile, flags in [("/bin/sh", ".profile", []), (shutil.which("zsh"), ".zprofile", ["-df"])]:
            with self.subTest(profile=profile):
                source = f'. "$HOME/{profile}"; '
                result = self.run_command([shell, *flags, "-c", source * 2 + 'printf "%s\\n" "$PATH"'])
                self.assertNotIn(str(self.test_home / ".docker/bin"), result.stdout.strip().split(":"))
                self.assertEqual(result.stderr, "")

    def test_git_identity_is_local_and_shared_preferences_are_portable(self):
        self.install()
        self.write(self.test_home / ".gitconfig.local", "[user]\n name = Example User\n email = example@example.invalid\n")
        git = shutil.which("git")
        self.assertEqual(self.run_command([git, "config", "--get", "user.email"]).stdout.strip(), "example@example.invalid")
        self.assertEqual(self.run_command([git, "config", "--get", "core.autocrlf"]).stdout.strip(), "input")
        self.assertNotIn("/Users/", (self.test_home / ".gitconfig").read_text())

    def test_tool_status_is_explicit_and_updates_are_opt_in(self):
        self.install()
        self.status_spies()
        result = self.shell('tool-status; print -- --updates--; tool-status --updates', flags="-di")
        self.assertIn("bun", result.stdout)
        calls = (self.root / "command-log").read_text().splitlines()
        self.assertEqual(sum("outdated" in line for line in calls), 2)
        invalid = self.run_command(
            [shutil.which("zsh"), "-di", "-c", "tool-status --invalid"], check=False,
        )
        self.assertEqual(invalid.returncode, 2)

    def status_spies(self):
        self.env["DOTFILES_TEST_COMMAND_LOG"] = str(self.root / "command-log")
        scripts = {
            "bun": 'printf "1.4.2\\n"\n',
            "vercel": 'printf "Vercel CLI 50.10.0\\n" >&2\n',
            "brew": '''case "$1" in
  --version) printf "Homebrew 7.0.7-103-ga57af19\\n" ;;
  outdated)
    if [ -n "${DOTFILES_TEST_UPDATE_GATE:-}" ]; then
      touch "$DOTFILES_TEST_UPDATE_STARTED"
      while [ ! -f "$DOTFILES_TEST_UPDATE_GATE" ]; do sleep 0.02; done
    fi
    [ "${DOTFILES_TEST_BREW_FAIL:-0}" = 0 ] || exit 7
    if [ "${DOTFILES_TEST_BREW_WARNING:-0}" = 1 ]; then
      printf "Warning: synthetic metadata refresh failure\\n" >&2
    fi
    if [ "${DOTFILES_TEST_BREW_PROGRESS:-0}" = 1 ]; then
      printf "==> Downloading package API metadata\\n" >&2
    fi
    printf '%s' "${DOTFILES_TEST_OUTDATED:-}"
    ;;
  *) exit 9 ;;
esac
''',
            "curl": '''[ "${DOTFILES_TEST_CURL_FAIL:-0}" = 0 ] || exit 6
printf '%s' "${DOTFILES_TEST_VERCEL_JSON:-}"
''',
        }
        for name, script in scripts.items():
            self.write(
                self.test_home / ".local/bin" / name,
                '#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$DOTFILES_TEST_COMMAND_LOG"\n' + script,
                executable=True,
            )
        installed = {name: [{"version": version, "installed": True, "active": True}]
                     for name, version in {"bun": "1.4.2", "npm:agent-browser": "0.8.4", "turbo": "2.7.4",
                                           "neon": "8.0.8", "vercel": "50.10.0"}.items()}
        self.env["DOTFILES_TEST_MISE_INSTALLED"] = json.dumps(installed)
        self.env["DOTFILES_TEST_OUTDATED"] = brew_updates("bun", "mise", "neonctl", "poppler")
        self.env["DOTFILES_TEST_VERCEL_JSON"] = '{"version":"50.11.0"}'
        self.write(self.test_home / ".local/bin/mise", "#!" + sys.executable + "\n" + r'''import json, os, sys
with open(os.environ["DOTFILES_TEST_COMMAND_LOG"], "a") as output:
    output.write("mise " + " ".join(sys.argv[1:]) + "|offline=" + os.environ.get("MISE_OFFLINE", "") + "\n")
args = sys.argv[3:]
if args == ["ls", "--current", "--json"]:
    assert os.environ["MISE_OFFLINE"] == "1"
    print(os.environ["DOTFILES_TEST_MISE_INSTALLED"])
elif args == ["outdated", "--global", "--json"]:
    assert os.environ["MISE_AUTO_INSTALL"] == "false"
    if os.environ.get("DOTFILES_TEST_CURL_FAIL") == "1": sys.exit(6)
    latest = json.loads(os.environ["DOTFILES_TEST_VERCEL_JSON"])["version"]
    current = json.loads(os.environ["DOTFILES_TEST_MISE_INSTALLED"])
    result = {}
    for name, entries in current.items():
        if name == "bun": continue
        try:
            newer = tuple(map(int, latest.split("."))) > tuple(map(int, entries[0]["version"].split(".")))
        except ValueError:
            newer = True
        if newer: result[name] = {"latest": latest}
    print(json.dumps(result))
elif args[:3] == ["upgrade", "--global", "--dry-run"]:
    print("Mise upgrade preview")
else:
    sys.exit(9)
''', executable=True)
        return self.state / "cache/dotfiles/tool-status/status-v2.txt"

    def enable_status_banner(self):
        self.write(self.test_home / ".config/zsh/options.local.zsh", "DOTFILES_TOOL_STATUS_ON_STARTUP=1\n")

    def terminal_shell(self, overrides=""):
        self.write(self.test_home / ".config/zsh/local.zsh", "PROMPT='test> '\nRPROMPT='keep'\nbindkey -e\n" + overrides)
        terminal = TerminalSession(self.test_home, self.env)
        self.addCleanup(terminal.close)
        return terminal

    def wait_for(self, condition, timeout=5, terminal=None):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            if terminal is None:
                time.sleep(0.02)
            else:
                # A real terminal drains echo and redraws as the user types.
                terminal.read_for(0.02)
        self.assertTrue(condition())

    def test_update_check_reports_versions_and_notices_and_keeps_cache_private(self):
        self.install()
        cache = self.status_spies()
        result = self.shell("tool-status --updates", flags="-di")
        self.assertIn("bun           v1.4.2", result.stdout)
        self.assertIn("vercel        v50.10.0 (update available: v50.11.0)", result.stdout)
        self.assertIn("(4 package updates available)", result.stdout)
        for name in ("bun", "mise", "neonctl", "poppler"):
            self.assertIn(f"    {name}: 1.0.0 -> 2.0.0", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertEqual(cache.read_text(), result.stdout)
        self.assertEqual(cache.stat().st_mode & 0o777, 0o600)
        self.assertEqual(cache.parent.stat().st_mode & 0o777, 0o700)
        calls = (self.root / "command-log").read_text()
        self.assertEqual(calls.count("outdated --json=v2"), 1)
        self.assertIn("outdated --global --json", calls)
        self.assertNotIn(" upgrade", calls)
        self.assertNotIn(" install ", calls)

    def test_up_to_date_and_failed_checks_are_distinct(self):
        self.install()
        self.status_spies()
        self.env["DOTFILES_TEST_OUTDATED"] = brew_updates()
        # Compare numeric components; 50.9.9 is older than 50.10.0.
        self.env["DOTFILES_TEST_VERCEL_JSON"] = '{"version":"50.9.9"}'
        current = self.shell("tool-status --updates", flags="-di")
        self.assertIn("Homebrew      v7.0.7-103-ga57af19\n", current.stdout)
        self.assertIn("vercel        v50.10.0\n", current.stdout)
        self.assertNotIn("no update", current.stdout)
        self.env["DOTFILES_TEST_BREW_FAIL"] = "1"
        self.env["DOTFILES_TEST_CURL_FAIL"] = "1"
        failed = self.shell("tool-status --updates", flags="-di")
        self.assertEqual(failed.stdout.count("(update check unavailable)"), 6)
        self.assertNotIn("no update", failed.stdout)

    def test_invalid_public_release_metadata_is_unavailable(self):
        self.install()
        self.status_spies()
        marker = self.root / "must-not-execute"
        self.env["DOTFILES_TEST_VERCEL_JSON"] = json.dumps({"version": f"$(touch {marker})"})
        result = self.shell("tool-status --updates", flags="-di")
        self.assertIn("vercel        v50.10.0 (update check unavailable)", result.stdout)
        self.assertFalse(marker.exists())

    def test_metadata_warning_does_not_claim_homebrew_is_up_to_date(self):
        self.install()
        self.status_spies()
        self.env["DOTFILES_TEST_OUTDATED"] = brew_updates()
        self.env["DOTFILES_TEST_BREW_WARNING"] = "1"
        result = self.shell("tool-status --updates", flags="-di")
        self.assertIn("Homebrew      v7.0.7-103-ga57af19 (update check unavailable)", result.stdout)
        self.assertNotIn("synthetic", result.stdout)

    def test_brew_progress_keeps_full_formula_and_cask_update_list(self):
        self.install()
        self.status_spies()
        self.env["DOTFILES_TEST_BREW_PROGRESS"] = "1"
        data = json.loads(brew_updates("oven-sh/bun/bun", "mise", "qpdf", "poppler"))
        data["casks"] = [{"name": "docker-desktop", "installed_versions": ["4.93.0,123"],
                          "current_version": "4.94.0,456", "pinned": True}]
        self.env["DOTFILES_TEST_OUTDATED"] = json.dumps(data)
        result = self.shell("tool-status --updates", flags="-di")
        self.assertIn("bun           v1.4.2", result.stdout)
        self.assertIn("(5 package updates available)", result.stdout)
        self.assertIn("poppler: 1.0.0 -> 2.0.0", result.stdout)
        self.assertIn("docker-desktop: 4.93.0,123 -> 4.94.0,456 [pinned]", result.stdout)
        self.assertNotIn("(update check unavailable)", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_brew_invalid_metadata_is_unavailable_without_partial_rows(self):
        self.install()
        self.status_spies()
        marker = self.root / "must-not-execute"
        data = json.loads(brew_updates("mise", "poppler"))
        data["formulae"][1]["name"] = f"$(touch {marker})"
        for invalid in (json.dumps(data), "invalid json"):
            self.env["DOTFILES_TEST_OUTDATED"] = invalid
            result = self.shell("tool-status --updates", flags="-di")
            self.assertIn("Homebrew      v7.0.7-103-ga57af19 (update check unavailable)", result.stdout)
            self.assertNotIn("mise: 1.0.0", result.stdout)
        self.assertFalse(marker.exists())

    def test_mise_checks_cover_globals_without_running_clis(self):
        self.install()
        self.status_spies()
        marker = self.root / "global-cli-ran"
        for name in ("agent-browser", "turbo", "neon", "vercel"):
            self.write(self.test_home / ".local/bin" / name, f"#!/bin/sh\ntouch '{marker}'\nexit 9\n", executable=True)
        result = self.shell("tool-status --updates", flags="-di")
        calls = (self.root / "command-log").read_text()
        self.assertEqual(calls.count("outdated --global --json"), 1)
        self.assertNotIn("registry.npmjs.org", calls)
        self.assertIn("neon          v8.0.8", result.stdout)
        self.assertIn("turbo         v2.7.4", result.stdout)
        self.assertIn("agent-browser v0.8.4", result.stdout)
        self.assertFalse(marker.exists())

    def test_cargo_backend_metadata_uses_short_name_without_running_the_tool(self):
        self.install()
        self.status_spies()
        installed = json.loads(self.env["DOTFILES_TEST_MISE_INSTALLED"])
        installed["tokei"] = [{"version": "14.0.0", "installed": True, "active": True}]
        self.env["DOTFILES_TEST_MISE_INSTALLED"] = json.dumps(installed)
        self.env["DOTFILES_TEST_VERCEL_JSON"] = '{"version":"15.0.0"}'
        marker = self.root / "tokei-ran"
        self.write(self.test_home / ".local/bin/tokei", f"#!/bin/sh\ntouch '{marker}'\n", executable=True)
        result = self.shell("tool-status --updates", flags="-di")
        self.assertIn("tokei         v14.0.0 (update available: v15.0.0)", result.stdout)
        self.assertFalse(marker.exists())

    def test_missing_global_is_reported_without_fetch_and_manual_status_is_offline(self):
        self.install()
        self.status_spies()
        data = json.loads(self.env["DOTFILES_TEST_MISE_INSTALLED"])
        del data["neon"]
        self.env["DOTFILES_TEST_MISE_INSTALLED"] = json.dumps(data)
        result = self.shell("tool-status", flags="-di")
        self.assertIn("neon          not installed or version unavailable (desired: 8)", result.stdout)
        self.assertNotIn("registry.npmjs.org", (self.root / "command-log").read_text())
        self.shell("tool-status --updates", flags="-di")
        self.assertNotIn("https://registry.npmjs.org/neon/latest", (self.root / "command-log").read_text())

    def test_shared_status_cache_uses_global_tools_and_preserves_project_paths(self):
        self.install()
        self.status_spies()
        project = self.root / "project"
        marker = self.root / "project-tool-ran"
        for tool in ("bun", "vercel", "brew", "curl", "python3", "mise"):
            self.write(project / "node_modules/.bin" / tool, f"#!/bin/sh\ntouch '{marker}'\nexit 9\n", executable=True)
        self.env["DOTFILES_TEST_PROJECT"] = str(project)
        result = self.shell('''
cd "$DOTFILES_TEST_PROJECT"
tool-status --updates
[[ "$path[1]" == "$DOTFILES_TEST_PROJECT/node_modules/.bin" ]]
''', flags="-di")
        self.assertIn("v1.4.2", result.stdout)
        self.assertIn("v50.10.0", result.stdout)
        self.assertFalse(marker.exists())

    def test_fresh_cached_banner_runs_no_commands_and_prints_once(self):
        self.install()
        cache = self.status_spies()
        self.shell("tool-status --updates", flags="-di")
        self.enable_status_banner()
        marker = self.root / "must-not-execute"
        # Cached text must not be sourced as shell code.
        with cache.open("a") as output:
            output.write(f"$(touch {marker})\n")
        (self.root / "command-log").unlink()
        result = self.shell('source "$HOME/.zshrc"; source "$HOME/.zshrc"', flags="-di")
        self.assertEqual(result.stdout, cache.read_text())
        self.assertEqual(result.stdout.count("Tool status:"), 1)
        self.assertEqual(result.stderr, "")
        self.assertFalse((self.root / "command-log").exists())
        self.assertFalse(marker.exists())

    def test_legacy_cache_hides_no_update_notices_without_fetching(self):
        self.install()
        cache = self.status_spies()
        self.write(cache, "Tool status:\n  Homebrew      v7.0.8 (no updates available)\n"
                          "  Vercel CLI    v63.1.0 (no update available)\n"
                          "  Turbo         v2.7.4 (update available: v2.11.7)\n")
        self.enable_status_banner()
        result = self.shell(":", flags="-di")
        self.assertNotIn("no update", result.stdout)
        self.assertIn("Homebrew      v7.0.8\n", result.stdout)
        self.assertIn("Vercel CLI    v63.1.0\n", result.stdout)
        self.assertIn("update available: v2.11.7", result.stdout)
        self.assertFalse((self.root / "command-log").exists())

    def test_stale_banner_is_nonblocking_atomic_and_deduplicates_workers(self):
        self.install()
        cache = self.status_spies()
        original = self.shell("tool-status --updates", flags="-di").stdout
        self.enable_status_banner()
        os.utime(cache, (0, 0))
        gate = self.root / "release-update"
        started = self.root / "update-started"
        self.env["DOTFILES_TEST_UPDATE_GATE"] = str(gate)
        self.env["DOTFILES_TEST_UPDATE_STARTED"] = str(started)
        self.env["DOTFILES_TEST_OUTDATED"] = brew_updates("replacement")
        (self.root / "command-log").unlink()
        try:
            # The check cannot finish until this test opens the gate, but each
            # terminal must return and display the complete previous snapshot.
            for _ in range(3):
                result = subprocess.run(
                    [shutil.which("zsh"), "-di", "-c", ":"], cwd=self.test_home,
                    env=self.env, text=True, capture_output=True, timeout=3,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, original)
                self.assertEqual(result.stderr, "")
            deadline = time.monotonic() + 5
            while not started.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(started.exists())
            self.assertEqual(cache.read_text(), original)
            self.assertEqual((self.root / "command-log").read_text().count("outdated --json=v2"), 1)
        finally:
            gate.touch()
            deadline = time.monotonic() + 5
            while "replacement: 1.0.0 -> 2.0.0" not in cache.read_text() and time.monotonic() < deadline:
                time.sleep(0.02)
        self.assertIn("replacement: 1.0.0 -> 2.0.0", cache.read_text())
        self.assertEqual(list(cache.parent.glob("status.*")), [])

    def test_first_banner_with_no_cache_returns_before_worker_finishes(self):
        self.install()
        cache = self.status_spies()
        self.enable_status_banner()
        gate = self.root / "release-first-update"
        self.env["DOTFILES_TEST_UPDATE_GATE"] = str(gate)
        self.env["DOTFILES_TEST_UPDATE_STARTED"] = str(self.root / "first-update-started")
        try:
            result = subprocess.run(
                [shutil.which("zsh"), "-di", "-c", ":"], cwd=self.test_home,
                env=self.env, text=True, capture_output=True, timeout=3,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            self.assertFalse(cache.exists())
        finally:
            gate.touch()
            deadline = time.monotonic() + 5
            while not cache.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
        self.assertIn("v50.11.0", cache.read_text())

    @isolated_terminal_test
    def test_refresh_animation_preserves_typed_input_and_prompt_then_cleans_up(self):
        self.install()
        cache = self.status_spies()
        self.shell("tool-status --updates", flags="-di")
        self.enable_status_banner()
        os.utime(cache, (0, 0))
        gate = self.root / "release-animation"
        self.env["DOTFILES_TEST_UPDATE_GATE"] = str(gate)
        self.env["DOTFILES_TEST_UPDATE_STARTED"] = str(self.root / "animation-started")
        terminal = self.terminal_shell()
        try:
            terminal.until("⠋ tools")
            terminal.send('print -r -- preserved-input > "$HOME/typed-proof"')
            terminal.until("⠹ tools")
            self.assertIn(b"test> ", terminal.output)
            self.assertNotIn(b"Cached results are stale", terminal.output)
            gate.touch()
            terminal.until("✓ tools")
            terminal.read_for(1.8)
            terminal.send("\n")
            typed = self.test_home / "typed-proof"
            self.wait_for(lambda: typed.exists() and typed.read_text() == "preserved-input\n", terminal=terminal)
            terminal.send('print -r -- "$PROMPT|$RPROMPT|${_DOTFILES_TOOL_STATUS_FD:-closed}" > "$HOME/prompt-proof"; zle -F -L >> "$HOME/prompt-proof"\n')
            proof = self.test_home / "prompt-proof"
            self.wait_for(lambda: proof.exists() and "closed" in proof.read_text(), terminal=terminal)
            self.assertEqual(proof.read_text(), "test> |keep|closed\n")
        finally:
            gate.touch()
            self.wait_for(lambda: cache.stat().st_mtime > 0)

    @isolated_terminal_test
    def test_refresh_animation_stays_silent_during_commands_and_discards_old_ticks(self):
        self.install()
        cache = self.status_spies()
        self.enable_status_banner()
        gate = self.root / "release-busy-refresh"
        self.env["DOTFILES_TEST_UPDATE_GATE"] = str(gate)
        self.env["DOTFILES_TEST_UPDATE_STARTED"] = str(self.root / "busy-refresh-started")
        terminal = self.terminal_shell()
        command_gate = self.test_home / "release-command"
        try:
            terminal.until("⠋ tools")
            terminal.send('touch "$HOME/command-started"; while [[ ! -f "$HOME/release-command" ]]; do sleep 0.02; done\n')
            self.wait_for(lambda: (self.test_home / "command-started").exists(), terminal=terminal)
            terminal.read_for(0.1)
            before = len(terminal.output)
            gate.touch()
            self.wait_for(cache.exists)
            terminal.read_for(1.8)
            self.assertEqual(terminal.output[before:], b"")
            command_gate.touch()
            terminal.read_for(0.3)
            terminal.send('print -r -- "${_DOTFILES_TOOL_STATUS_FD:-closed}" > "$HOME/busy-proof"\n')
            proof = self.test_home / "busy-proof"
            self.wait_for(lambda: proof.exists() and proof.read_text() == "closed\n", terminal=terminal)
            self.assertNotIn(b"tools", terminal.output[before:])
        finally:
            gate.touch()
            command_gate.touch()
            self.wait_for(cache.exists)

    @isolated_terminal_test
    def test_failed_refresh_shows_failure_and_closes_animation_descriptor(self):
        self.install()
        cache = self.status_spies()
        self.enable_status_banner()
        terminal = self.terminal_shell("_dotfiles_tool_status_collect() { return 9; }\n")
        terminal.until("! tools")
        self.assertNotIn("✓ tools".encode(), terminal.output)
        terminal.read_for(1.8)
        terminal.send('print -r -- "${_DOTFILES_TOOL_STATUS_FD:-closed}" > "$HOME/failure-proof"; zle -F -L >> "$HOME/failure-proof"\n')
        proof = self.test_home / "failure-proof"
        self.wait_for(lambda: proof.exists() and proof.read_text() == "closed\n", terminal=terminal)
        self.assertFalse(cache.exists())

    def test_literal_token_is_blocked_but_runtime_reference_is_allowed(self):
        sample = self.root / "scanner"
        token = "fixture_" + "q" * 32
        assignment = "export " + "UIDOTSH_TOKEN" + "="
        self.write(sample / "shell.zsh", assignment + '"' + token + '"\n')
        args = [shutil.which("gitleaks"), "dir", "--redact", "--no-banner", "--config", str(REPO / ".gitleaks.toml"), str(sample)]
        blocked = self.run_command(args, check=False)
        self.assertEqual(blocked.returncode, 1)
        self.write(sample / "shell.zsh", assignment + '"$TOKEN_FROM_SESSION"\n')
        self.run_command(args)

    def test_precommit_hook_blocks_a_staged_literal_token(self):
        fixture = self.root / "git-fixture"
        fixture.mkdir()
        git = shutil.which("git")
        self.run_command([git, "init", "--quiet", str(fixture)])
        shutil.copyfile(REPO / ".gitleaks.toml", fixture / ".gitleaks.toml")
        assignment = "export " + "UIDOTSH_TOKEN" + "="
        self.write(fixture / "shell.zsh", assignment + '"' + "fixture_" + "q" * 32 + '"\n')
        self.run_command([git, "add", "."], cwd=fixture)
        result = self.run_command(["/bin/sh", str(REPO / ".githooks/pre-commit")], cwd=fixture, check=False)
        self.assertEqual(result.returncode, 1)

    def test_precommit_hook_allows_clean_staged_files(self):
        fixture = self.root / "clean-git-fixture"
        fixture.mkdir()
        git = shutil.which("git")
        self.run_command([git, "init", "--quiet", str(fixture)])
        shutil.copyfile(REPO / ".gitleaks.toml", fixture / ".gitleaks.toml")
        self.write(fixture / "shell.zsh", "export EDITOR=vim\n")
        self.run_command([git, "add", "."], cwd=fixture)
        result = self.run_command(["/bin/sh", str(REPO / ".githooks/pre-commit")], cwd=fixture)
        self.assertEqual(result.stderr, "")

    def test_precommit_hook_rejects_scanner_error_with_success_exit(self):
        fixture = self.root / "scanner-error-fixture"
        fixture.mkdir()
        self.run_command([shutil.which("git"), "init", "--quiet", str(fixture)])
        spies = self.root / "scanner-spies"
        self.write(spies / "gitleaks", '#!/bin/sh\nprintf "synthetic backend error\\n" >&2\nexit 0\n', executable=True)
        self.env["PATH"] = str(spies) + ":" + self.env["PATH"]
        result = self.run_command(["/bin/sh", str(REPO / ".githooks/pre-commit")], cwd=fixture, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("scanner error", result.stderr)
        self.assertNotIn("synthetic backend error", result.stderr)

    def test_precommit_hook_preserves_nonzero_scanner_exit(self):
        fixture = self.root / "scanner-exit-fixture"
        fixture.mkdir()
        self.run_command([shutil.which("git"), "init", "--quiet", str(fixture)])
        spies = self.root / "scanner-spies"
        self.write(spies / "gitleaks", '#!/bin/sh\nexit 7\n', executable=True)
        self.env["PATH"] = str(spies) + ":" + self.env["PATH"]
        result = self.run_command(["/bin/sh", str(REPO / ".githooks/pre-commit")], cwd=fixture, check=False)
        self.assertEqual(result.returncode, 7)

    def test_backup_restore_preserves_originals_and_leaves_new_files(self):
        self.write(self.test_home / ".zshrc", "original shell\n")
        (self.test_home / ".zshrc").chmod(0o640)
        self.write(self.test_home / "original-git", "[user]\n name = Original\n")
        (self.test_home / ".gitconfig").symlink_to("original-git")
        backup = self.root / "backup"
        args = [shutil.which("python3"), str(REPO / "scripts/backup.py")]
        self.run_command(args + ["create", "--home", str(self.test_home), "--backup", str(backup)])
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((backup / "files/.zshrc").stat().st_mode & 0o777, 0o600)
        (self.test_home / ".gitconfig").unlink()
        self.install()
        self.run_command(args + ["restore", "--home", str(self.test_home), "--backup", str(backup)])
        self.assertEqual((self.test_home / ".zshrc").read_text(), "original shell\n")
        self.assertEqual((self.test_home / ".zshrc").stat().st_mode & 0o777, 0o640)
        self.assertTrue((self.test_home / ".gitconfig").is_symlink())
        self.assertEqual(os.readlink(self.test_home / ".gitconfig"), "original-git")
        self.assertTrue((self.test_home / ".config/zsh/environment.zsh").is_file())

    def test_corrupt_backup_is_rejected_before_restore_changes_live_files(self):
        self.write(self.test_home / ".zshrc", "original shell\n")
        backup = self.root / "backup"
        args = [shutil.which("python3"), str(REPO / "scripts/backup.py")]
        self.run_command(args + ["create", "--home", str(self.test_home), "--backup", str(backup)])
        self.install()
        installed = (self.test_home / ".zshrc").read_bytes()
        (backup / "files/.zshrc").write_text("corrupt backup\n")
        result = self.run_command(args + ["restore", "--home", str(self.test_home), "--backup", str(backup)], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.test_home / ".zshrc").read_bytes(), installed)

    def test_backups_cannot_be_created_inside_source_repository(self):
        result = self.run_command([
            shutil.which("python3"), str(REPO / "scripts/backup.py"), "create",
            "--home", str(self.test_home), "--backup", str(REPO / "backups" / "test"),
        ], check=False)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((REPO / "backups" / "test").exists())


if __name__ == "__main__":
    unittest.main()
