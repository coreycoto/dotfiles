# Setup

The supported baseline is Apple Silicon macOS with Xcode Command Line Tools,
Homebrew and Mise. A complete fresh-Mac bootstrap remains unverified; repository
checks install managed files into disposable homes on the current Mac.
Apple Terminal profiles, themes and application preferences are outside scope.

## Prerequisites and checkout

Install the Apple developer tools and Homebrew explicitly. Follow
[Mise installation](mise.md#bootstrap-the-official-binary) for the reviewed
official binary, then install the validation tools:

```sh
mise install python@3.15.2 chezmoi@latest gitleaks@latest shellcheck@latest uv@latest
```

Clone the published repository without applying it:

```sh
git clone https://github.com/coreycoto/dotfiles.git
cd dotfiles
./scripts/enable-hooks
MISE_OFFLINE=1 mise exec python@3.15.2 chezmoi@latest gitleaks@latest shellcheck@latest uv@latest -- ./scripts/check
```

Alternatively, `chezmoi init coreycoto/dotfiles` clones into chezmoi's default
source directory. Initialization alone does not activate the files. Run the
remaining commands from the reviewed repository checkout.

Only `home/` is installed: `.chezmoiroot` excludes repository documentation,
scripts, tests and package declarations from home-directory application.
`manifest.json` supplies the explicit managed-file inventory for validation and
backup/restore; see [scope](inventory.md).

## Prepare local settings

Before replacing a Git configuration, adapt `examples/gitconfig.example` into
the unmanaged `~/.gitconfig.local`. Preserve the existing name, email, signing
key, key format and signing policy. Application-specific diff/merge commands
and machine-specific `includeIf` blocks belong there too.

Zsh reads `~/.config/zsh/options.local.zsh` before its shared modules for theme,
installation locations and plugin options. It reads `~/.config/zsh/local.zsh`
last for aliases, functions, private settings and machine-specific PATH additions.
See [shell configuration](shell.md) and `examples/options.example.zsh`.

SSH reads `~/.ssh/config.local` before shared defaults. Preserve existing host,
identity and agent settings there; see [SSH setup](ssh.md). Keep private plugin
catalogs in the separate unmanaged
`~/.config/dotfiles/agent-plugin-sources.local.json` described in
[local plugin sources](agent-configuration.md#local-plugin-sources).

Keep credentials in a password manager or private local files with mode `600`.
Prefer retrieving them only for the commands that need them. Review existing
files for literal credentials before showing a chezmoi diff, which can display
the old contents. Do not put credentials in shared source, fixtures or commands
that enter shell history. Absence from Git does not establish that an exposed
credential was revoked.

## Back up and preview

Create a private backup outside the repository:

```sh
dotfiles_backup="$HOME/.local/state/dotfiles/backups/$(date +%Y%m%d-%H%M%S)"
python3 scripts/backup.py create --home "$HOME" --backup "$dotfiles_backup"
```

The helper covers manifest targets and the local overlays listed in its
`LOCAL_TARGETS`. Separately preserve any other files you intend to edit,
including an existing SSH `config.local` or private plugin source overlay.
Keep those copies outside Git with restricted permissions. The general helper
does not automatically restore additional copies; see [recovery](recovery.md).

Chezmoi uses the system permission mask unless configured otherwise. Adapt
`examples/chezmoi.example.toml` into a host-local configuration for private managed
files. Keep machine-specific source paths outside Git and use the same mask for
preview, apply and verification.

```sh
chezmoi --source "$PWD" managed --include=files
chezmoi --source "$PWD" status
chezmoi --source "$PWD" --no-pager diff
```

## Apply and verify

After reviewing the diff and choosing to activate it:

```sh
chezmoi --source "$PWD" apply --interactive
chezmoi --source "$PWD" verify
```

Keep the existing terminal open. Open another terminal and verify command
resolution, Git identity/signing, and entering and leaving project directories
before normal use. See [shell behavior](shell.md) for PATH precedence.

Software installation remains explicit. Continue with [Mise tools](mise.md),
[Oh My Zsh](oh-my-zsh.md), [VS Code](vscode.md) or [Codex](codex.md) as needed.
Applying chezmoi does not install plugins, grant trust, establish authentication
or replace Codex's main machine-state file. It does not remove old installations
or unmanaged files.
