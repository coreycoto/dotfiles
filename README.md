# Dotfiles

Portable Zsh, Git, runtime, VS Code and Codex configuration for macOS.
Mise owns the selected runtimes and developer CLIs; private settings stay in
unmanaged local overlays. Installation and software updates are explicit.

The supported baseline is Apple Silicon macOS with Xcode Command Line Tools,
Homebrew and Mise. A complete fresh-Mac bootstrap remains unverified.
Apple Terminal profiles, themes and application preferences are outside scope.

## Get started

Read [setup](docs/setup.md) for prerequisites, local settings and backups before
applying anything. With the validation tools installed:

```sh
git clone https://github.com/coreycoto/dotfiles.git
cd dotfiles
./scripts/enable-hooks
MISE_OFFLINE=1 ./scripts/check
chezmoi --source "$PWD" --no-pager diff
```

Review the diff, then follow [apply and verify](docs/setup.md#apply-and-verify).
Use [recovery](docs/recovery.md) to restore a selected backup.

## Documentation

- [Shell behavior and status banner](docs/shell.md)
- [Mise installation and tools](docs/mise.md)
- [Codex and plugin maintenance](docs/codex.md)
- [VS Code settings and extensions](docs/vscode.md)
- [All guides](docs/README.md)

Only `home/` is installed by chezmoi. `examples/` contains local-setting templates;
`scripts/` and `tests/` provide maintenance and disposable-home checks.
[manifest.json](manifest.json) lists the approved source-to-target mappings used
by validation and backup/restore. See [scope](docs/inventory.md) before adding files.

Licensed under the [MIT license](LICENSE).
