# VS Code preferences and extensions

Chezmoi manages only `~/.config/dotfiles/vscode/settings.json` and
`extensions.json`. These authored selections contain no machine paths or
account values. From the reviewed checkout, `scripts/vscode.py` explicitly
merges settings or installs extensions. It never manages an entire VS Code
directory, starts at shell login, or runs automatically during chezmoi apply.

## Portable settings

The portable settings retain the reviewed Git, Explorer, diff, inline suggestion,
terminal hint, header action, import update, and Biome configuration preferences.
The maintenance policy disables automatic extension updates in the
target profile, including updates for unrelated extensions. A local override can
retain automatic updates, but installed versions may then drift from the pins.
Selected settings are whole top-level keys; language blocks are not deep merged.

Existing language formatter choices stay local or in their projects. Choose
the formatter in workspace settings for each project. The official Biome extension supports
workspace configuration; `biome.requireConfiguration` avoids using Biome where
the project has not opted in. See [Biome's editor guidance](https://biomejs.dev/reference/vscode/).

AI/Copilot, Grammarly, preview tools, trust policy, trusted schema domains, and
other extension-specific preferences remain local. No default interpreter,
debugger launch configuration, account token, or private domain is imported.
Keybindings use VS Code defaults; existing custom keybindings on another machine
are retained. Review individual authored bindings before a future import.

`~/.vscode/argv.json` is a separate machine-local launch file; it is not a portable settings overlay. Authentication, global/workspace
storage, history, profiles metadata, logs, sync state, databases, and downloaded
extension directories remain outside Git. Never copy the complete `Code` or
`.vscode` directory into chezmoi source.

## Curated extension selection

`extensions.json` pins the directly selected IDs and versions:

| Extension | Purpose |
|---|---|
| `ms-python.python` | Python interpreter selection and editor integration |
| `ms-python.debugpy` | Graphical Python debugging |
| `charliermarsh.ruff` | Project-configured Python linting and formatting |
| `astral-sh.ty` | Python language and type checking services |
| `biomejs.biome` | Project-configured JavaScript/TypeScript tooling |
| `editorconfig.editorconfig` | Project EditorConfig rules |
| `github.vscode-github-actions` | GitHub Actions authoring |
| `oven.bun-vscode` | Bun editor integration |

Unselected extensions remain outside this declaration. The helper does not
uninstall them or update them to match a snapshot. New optional tools require
a deliberate selection change; Codex installation and authentication can remain
native machine choices.

Install a standard VS Code distribution and expose its `code` CLI through the
editor's supported platform procedure. This selection requires VS Code 1.100
or newer. Portable mode is not supported because
it can override data/extension directory selectors. See the [VS Code CLI](https://code.visualstudio.com/docs/configure/command-line).

## Preview and explicit application

Close windows using the target profile before applying so the editor cannot
overwrite the reviewed settings. Decide how that profile uses Settings Sync;
remote settings and extensions can otherwise replace local choices. The helper
does not sign in, alter sync accounts, or manage authentication.

For the Default profile, preview from the reviewed checkout:

```sh
python3 scripts/vscode.py settings
python3 scripts/vscode.py extensions
```

Preview reads the selected settings file and prints changed key names, without
displaying private values or running Code. Extension preview prints commands;
it does not read an installed inventory because the native CLI can create state.

Use optional entries from `examples/vscode-settings.example.json` in
`~/.config/dotfiles/vscode/settings.local.json`, outside Git. Existing local files
are preserved by chezmoi. Local values override portable values during explicit
merge; removal from the overlay does not automatically delete a previously
merged key. Remove obsolete keys deliberately in the editor.

After reviewing the target and selecting activation:

```sh
python3 scripts/vscode.py settings --apply
python3 scripts/vscode.py extensions --apply
```

The settings helper parses JSONC, rejects malformed or duplicate keys and file
symlinks, preserves unrelated text/comments, and atomically replaces only that
file after a private backup. Existing permissions are retained; new files use
mode `600`. Repeating it with the same inputs leaves the settings bytes unchanged.
The general backup helper also covers the unmanaged settings overlay.

For a named profile, create it in VS Code first and open **Preferences: Open User
Settings (JSON)** while that profile is active to identify its exact file. Pass
that file with `settings --settings-file` and the same name with
`extensions --profile`. Never guess the generated profile ID or assume that the
Default settings path configures a named profile. CLI listing requires the named
profile to exist. See [settings locations](https://code.visualstudio.com/docs/configure/settings)
and [profiles](https://code.visualstudio.com/docs/configure/profiles).

Extension application checks Code compatibility and inventories the target, then
installs only missing or different selected `publisher.extension@version` pins.
It uses the native `--do-not-include-pack-dependencies` flag to suppress pack
expansion; Python and Python Debugger are explicitly selected together. Python's
optional Pylance/environment-manager pack entries are not added automatically.
These are direct version pins, not a lockfile or an archive of extension binaries.
Marketplace availability and future dependency changes must be requalified.

The helper verifies selected versions and preserves the preexisting versions of
unrelated extensions. It never uses `--update-extensions`, uninstalls anything,
or retries a failed install. Private receipts and CLI logs record completed steps
under `~/.local/state/dotfiles/vscode`; an incomplete operation is reported and
retained for inspection before any fresh attempt.

## Disposable trial and Python debugging

Use a temporary home and distinct data/extension directories. The Default profile
inside these directories is disposable; this does not touch the normal Default
profile. The following POSIX trial uses the installed `code` executable:

```sh
trial=$(mktemp -d)
mkdir -p "$trial/home" "$trial/user-data/User" "$trial/extensions"
HOME="$trial/home" CFFIXED_USER_HOME="$trial/home" \
  python3 scripts/vscode.py settings \
  --settings-file "$trial/user-data/User/settings.json" --apply
HOME="$trial/home" CFFIXED_USER_HOME="$trial/home" \
  python3 scripts/vscode.py extensions --user-data-dir "$trial/user-data" \
  --extensions-dir "$trial/extensions" --apply
# Repeat both commands and inspect their receipts before retiring the trial.
env -u VSCODE_IPC_HOOK_CLI -u VSCODE_PORTABLE -u VSCODE_EXTENSIONS \
  HOME="$trial/home" CFFIXED_USER_HOME="$trial/home" \
  code --user-data-dir "$trial/user-data" --extensions-dir "$trial/extensions" \
  --sync off
```

The final command opens the trial editor; do not run it against the live data
directory accidentally. On Windows, set an equivalent temporary environment
and explicit paths rather than copying POSIX shell syntax.

Python runtimes remain mise/uv/project owned. In a disposable Python project,
create a project environment, use **Python: Select Interpreter**, set a breakpoint,
and run the **Python Debugger: Current File** configuration. If the project needs
custom launch settings, keep `.vscode/launch.json` in that project with debugger
type `debugpy`; avoid a fixed global interpreter path. See [Python debugging](https://code.visualstudio.com/docs/python/debugging).
ty normally disables the competing Python language server on activation; projects
that choose another language server should follow [ty's editor settings](https://docs.astral.sh/ty/editors/).
An installed debugger does not by itself establish graphical breakpoint behavior;
the disposable native CLI and a real debugger protocol trial are separate checks
from a manual editor UI smoke test.

CI checks use disposable files and a CLI fixture without downloads. A
downloaded debugger's protocol behavior, manual editor UI, Settings Sync and
non-macOS installation require their own checks.

## Updates and rollback

Change only reviewed versions in `extensions.json`, qualify compatibility and
project behavior in a fresh disposable profile, then explicitly apply the updated
selection. Do not replace the selection with the output of an all-installed
inventory, use an unversioned install command, or update all extensions as part
of curated maintenance. To retain exact versions, keep profile auto-updates off
and resolve conflicting Settings Sync behavior deliberately.

Each settings apply with changes records the prior file, mode, and SHA-256 in a
private receipt. Close the profile, review intervening edits, verify the backup
checksum, and restore `settings.before.json` to the receipt's target with its
original mode. If the target was originally absent, retain it unless its removal
is separately chosen after review. Do not commit backups or receipts.

An extension receipt records the previous versions and completed installs.
Restore only changed selected IDs to their recorded previous versions with
`code --install-extension publisher.extension@version --force` and the same
profile/directory selectors; inventory again afterward. Review newly added IDs
before individually removing them. A failed or unavailable old download is not
a completed rollback. Keep unrelated extensions, launch files, keybindings,
authentication, and databases in place throughout recovery.
