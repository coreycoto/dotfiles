# Mise installation and tools

Mise owns the authored runtime defaults and curated global CLIs. Homebrew keeps
desktop applications and existing native dependency stacks. The scope is the
selection in `home/dot_config/mise/config.toml`, not every installed package.
Global Bun follows `1` (Bun 1.x) with update checks every 6 hours and a 12-hour
release delay; Node/Python/Rust defaults and exact project selectors remain fixed.
Applying dotfiles and installing tools are explicit operations; no chezmoi hook
or shell startup installs software.

## Bootstrap the official binary

Follow [upstream installation](https://mise.jdx.dev/installing-mise.html#mise-run).
The verification steps below require GnuPG; see [local installation](gnupg.md#optional-installation-and-local-use)
if it is not installed.
Verify the installer with the documented release key in an isolated keyring:

```sh
mise_bootstrap_dir=$(mktemp -d)
mkdir -m 700 "$mise_bootstrap_dir/gpg"
gpg --homedir "$mise_bootstrap_dir/gpg" --batch \
  --keyserver hkps://keys.openpgp.org \
  --recv-keys 24853EC9F655CE80B48E6C3A8B81C9D17413A06D
curl -qfsSL https://mise.jdx.dev/install.sh.sig -o "$mise_bootstrap_dir/install.sh.sig"
gpg --homedir "$mise_bootstrap_dir/gpg" --batch \
  --output "$mise_bootstrap_dir/install.sh" --decrypt "$mise_bootstrap_dir/install.sh.sig"
```

Stop if verification fails. Confirm the signing fingerprint above, then install
the reviewed release explicitly. The signed installer contains that release's
archive checksums. Use the ordinary endpoint so it does not edit shell startup:

```sh
MISE_VERSION=v2026.10.7 MISE_INSTALL_PATH="$HOME/.local/bin/mise" \
  MISE_INSTALL_EXT=tar.gz MISE_INSTALL_FROM_GITHUB=1 MISE_INSTALL_HELP=0 \
  sh "$mise_bootstrap_dir/install.sh"
~/.local/bin/mise --version
```

Mise 2026.10.7 is the qualified baseline for `outdated --global`, the selected
update options and status JSON. Upgrade Mise itself deliberately with
`mise self-update`, then recheck these contracts. Retain any old Homebrew copy
until `command -v mise` and all regenerated shims resolve to the official binary.

## Install selected tools

Follow [setup](setup.md) to back up, preview and explicitly apply the configuration.
Then preview the authored software selection before installing it:

```sh
dotfiles-tools
dotfiles-tools --apply
mise reshim
```

The launcher requires the reviewed source and live Mise configuration to match.
It installs only the global selection. It does not execute project tasks or
remove an existing installation. Verify command paths from the home directory
and from a project with its own selector, including leaving that project.

Register the local `gh-steward` extension using
[tool ownership](tool-ownership.md#git-slop-and-gh-steward-distribution).
Native aqua/GitHub installs verify publisher checksums and available provenance.
Git-slop keeps schemas/resources in its release archive; gh-steward's
platform-named executable is installed as `gh-steward`.

Two integration details are part of the qualified setup. The shell supplies
`__MISE_BIN` for the official binary to avoid Mise 2026.10.7's macOS symlink
updater dispatch failure. Agent-browser uses `npm:agent-browser`: its package
includes the native executable and version-matched workflow assets, which the
standalone aqua download lacks. No Bun-global postinstall trust is added.

The selection also includes actionlint, cargo-deny, shfmt, SwiftFormat,
SwiftLint, Tokei, Codex CLI, Pandoc, yt-dlp and Mole. Update checks every 6 hours
follow the authored requests. Keep existing installations until replacement
workflows have been verified.
Tokei uses `cargo:tokei` with `features = "all"` to preserve serialization support.
The yt-dlp request selects the standalone macOS asset. Mole is macOS-only and
requires its source scripts, resource links and matching native helpers; qualify
version/help and a bounded read-only analysis before switching command ownership.
Use Mise for updates instead of `mo update` or `yt-dlp --update`.

## Verification and recovery

```sh
MISE_OFFLINE=1 mise ls --current
MISE_OFFLINE=1 mise which bun
MISE_OFFLINE=1 bun --version
MISE_OFFLINE=1 git-slop --version
MISE_OFFLINE=1 gh steward version --json
tool-status
tool-status --updates
mise doctor
```

Verify the remaining selected CLIs with their version/help contracts, including
agent-browser's native invocation and an actual browser path when a browser is
already installed. CLI installation alone does not prove browser availability,
GitHub permissions, Vercel/Neon authentication, Linux/Windows qualification or
publisher release automation. Keep those evidence boundaries explicit.

Global command-triggered update opt-ins do not alter project selectors or pinned
consumer acquisition. Offline status collection must not modify Mise install or
update state. No updater service is installed. Old versions are retained rather
than pruned automatically.

To recover configuration, use the selected [private backup](recovery.md) and
regenerate shims with the intended Mise binary. Restore any separately saved
runtime or PATH choices deliberately. Dotfiles restoration does not reinstall
packages or restore removed Homebrew kegs. Preserve unrelated project selectors,
installed versions and caches while diagnosing a failure.
