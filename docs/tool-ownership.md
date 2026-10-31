# Tool ownership and project versions

| Tool or role | Installation owner | Version selection |
|---|---|---|
| Mise | Official release binary in `~/.local/bin/mise` | Verified installer; explicit `mise self-update` |
| Node, Python, Rust | Mise | Exact defaults in `~/.config/mise/config.toml`; project selectors override them |
| Bun | Mise | Global `1` follows Bun 1.x with update checks every 6 hours; exact project selectors override it |
| chezmoi, gh, Git LFS, Gitleaks, ShellCheck, uv | Mise registry backends | Global `latest`, command-triggered update checks every 6 hours |
| ripgrep, fd, fzf, zoxide, bat | Mise registry backends | Global `latest`, command-triggered update checks every 6 hours; optional shell integration stays local |
| actionlint, Lefthook, cargo-deny, shfmt, SwiftFormat, SwiftLint, Codex CLI, Pandoc | Mise registry backends | Global `latest`, update checks every 6 hours; Swift binaries are selected on macOS |
| Tokei | Mise Cargo backend | Global `latest`, update checks every 6 hours; `features = "all"` preserves JSON/CBOR/YAML support |
| yt-dlp | Mise GitHub backend | Global `latest`, update checks every 6 hours; publisher's standalone macOS executable |
| Mole | Mise GitHub backend | Global `latest`, update checks every 6 hours on macOS; source scripts and native helpers |
| agent-browser | Mise's npm backend, including native binary and matching skills | Global `latest`; browser download remains explicit |
| Vercel CLI, Turbo, Neon | Mise's npm backend, using Bun in isolated per-tool directories | Vercel `latest`, Turbo `2`, Neon `8`; command-triggered update checks every 6 hours |
| git-slop, gh-steward | Mise's GitHub backend, using existing publisher releases | Global `0.16` and `0.6` ranges; consumer automation keeps its own exact pins |
| `gh steward` entry point | Local GitHub CLI extension wrapper | Forwards to the Mise-managed executable |
| Docker Desktop, Docker CLI, Buildx, Compose | Homebrew cask `docker-desktop` | Explicit Homebrew maintenance |
| FFmpeg, ImageMagick, Poppler and existing native dependencies | Homebrew | Preserve existing packages; changes require dependent and workflow checks |
| Git and Apple development tools, Swift compiler, SDKs, SwiftPM | macOS / selected Xcode installation | Project toolchain and SDK requirements; [SwiftPM collections](swiftpm.md) |
| GnuPG and pinentry, when needed | Explicit optional Homebrew installation | [Default preferences and local use](gnupg.md) |
| SSH client and inherited agent | macOS / existing host installation | [Portable config and local agent selection](ssh.md) |
| Oh My Zsh | Explicit `scripts/oh-my-zsh.py` Git installation | Reviewed commit in `tools/oh-my-zsh.json`; [update and rollback](oh-my-zsh.md) |
| TypeScript, tsx, project Vercel/Wrangler/Turbo, Portless | Project package manager | Project manifest and lockfile; [Portless onboarding](portless.md) |
| .NET SDKs | Existing host SDK installation | Project `global.json`, including roll-forward policy |
| Python dependencies and virtual environments | uv / project tooling | Project manifest and lockfile; installed Mise interpreter |

The exact runtime defaults are Node 26.13.0, Python 3.15.2 and Rust 1.99.1
with rustfmt and Clippy. Bun follows the `1` request: any stable Bun 1.x release
can become the global default after the release delay and a due command-triggered
update. Project Bun pins remain exact. Mise's Rustup and Cargo directories stay
isolated under `~/.local/share/dotfiles`. Switching PATH ownership does not
uninstall prior tools. Preserve existing installations until their dependents
and replacement workflows are checked; see [recovery](recovery.md) and
[Rust configuration](rust.md).

Do not replace GNU coreutils with Mise's `coreutils` shorthand: that entry
installs uutils. Keep dependency-heavy packages and casks in Homebrew.
Other Homebrew installations remain outside the curated selection and can
still appear in Homebrew update metadata. Removing them requires a separate
dependent review and recovery plan.

See [developer CLI tools](developer-cli-tools.md) and the
[agent tool skill catalog](agent-tool-skills.md) for focused references.

## Explicit installation

Install Mise once using the official binary, following the signed-script
procedure in [Mise installation](mise.md). Do not use the shell-specific
installer endpoints: the dotfiles already own startup and shim PATH setup.
Keep `~/.local/bin` ahead of Homebrew and verify `command -v mise`.

After reviewing and applying the dotfiles, preview the authored selection:

```sh
dotfiles install --dry-run
# Installs the global selection only after the source and live configs match:
dotfiles install
mise reshim
```

On a fresh machine, install the validation prerequisites first as shown in the
[setup guide](setup.md). The launcher uses the reviewed checkout recorded by
chezmoi and always runs Mise from the home directory. It does not execute project tasks or change
project configuration. If the checkout moves, reapply the launcher.

Mise shims follow `~/.local/bin` and precede retained Bun globals and Homebrew.
Project bins still come first. Login and interactive shells share stable shim
paths. Startup does not activate Mise, install missing tools, or perform upgrades.
An explicitly missing project version fails without falling back to another
version; all three missing-tool auto-install settings remain disabled.

The shell exports `__MISE_BIN` only when the official binary exists. Mise
2026.10.7 otherwise relaunches some macOS symlinks under the tool's name during
an automatic update. This keeps its updater on the real Mise entry point.
Requalify the workaround after upgrading Mise before removing it.

The former Homebrew Bun symlink must be replaced with a real Mise installation
before retiring any keg. Record and preserve that symlink, install and qualify
the same exact Bun version, then switch the installation path. Never remove or
modify the symlink's Cellar target. Do not run `bun upgrade` on a managed binary.

## Project selection

Read each project's `packageManager`, runtime engine requirements, CI versions,
`.python-version`, Rust toolchain/MSRV, `mise.toml`, and `.NET global.json`.
Preserve distinct Docker, CI, and minimum-supported-version boundaries.
An engine compatibility range is a constraint, not an exact runtime pin.

Projects own durable team-wide selectors. This dotfiles repository does not
publish a list of private project names or paths. For an existing checkout,
prepare an explicit machine-local selection without changing tracked source:

```sh
python3 scripts/project-tools.py --project /path/to/project \
  --tool node@24.21.0 --tool bun@1.3.14
# Review the preview, then repeat with --apply.
```

The helper writes `mise.local.toml` with only the selected tools and adds its
anchored ignore rule to that checkout's Git exclude file. It preserves existing
exclude rules and refuses a differing selector, tracked selector, or symlink.
It does not install, execute, or trust project tasks or environment files.
Record the project requirements that justified each choice outside this repo.
To change an existing selector, review that file manually; do not replace an
unrelated local configuration. See [mise configuration](https://mise.jdx.dev/configuration.html).

Verify from the project directory, including nested SDK roots where required:

```sh
mise which node
node --version
bun --version
python3 --version
rustc --version
dotnet --version
```

Run only the commands relevant to that project. The managed `~/.config/uv/uv.toml`
sets `python-preference = "only-system"` and `python-downloads = "never"` so uv
uses installed interpreters rather than maintaining a second Python installation.
Its existing downloaded copies are retained. Project uv settings can override
user defaults; a project that needs another Python version should install it
explicitly through mise first. Verify `uv python find --system --show-version`.
For an explicit choice when creating or syncing an environment, use
`uv venv --python "$(mise which python)" --no-python-downloads`. Existing virtual
environments keep their interpreter until an intentional rebuild.
Source project versions and hosted CI are independent of these local selectors.
Changing team-wide versions requires the owning project's normal review.
See [uv interpreter preferences](https://docs.astral.sh/uv/reference/settings/#python-preference)
and [configuration precedence](https://docs.astral.sh/uv/concepts/configuration-files/).

## Global CLIs and automatic updates

`~/.config/mise/config.toml` is the authored tool selection. Native CLI registry
entries use aqua or GitHub releases. The npm backend installs Vercel, Turbo,
`npm:neon` and `npm:agent-browser` separately, using the Mise-owned Bun as
installer. It does not use the old shared Bun global installation.
Agent-browser's npm package bundles its native executable and matching workflow
assets; the standalone aqua asset omits those assets. Bun blocks its postinstall
script, and the packaged launcher runs the bundled executable.
`agent-browser install` remains an explicit browser download.

Each selected global CLI and Bun sets `auto_update = "6h"`. A due check through a shim
or `mise exec` upgrades that tool within its request before running it. Exact
Node/Python/Rust defaults and project-owned pins stay fixed. Failed updates warn and use
the installed version. Releases normally wait at least 12 hours; replaced
versions are retained (`upgrade.auto_prune = false`). No background service is
installed. Project adapters that require exact git-slop or gh-steward provenance
continue using their own locked acquisition path.

Tokei uses the explicit `cargo:tokei` backend because current upstream releases
have no prebuilt assets. Its Cargo `all` feature matches Homebrew's serialization
support. Actionlint uses `aqua:rhysd/actionlint` to preserve the existing tool;
the registry shorthand recommends a different fork. SwiftFormat and SwiftLint remain CLI installations; Xcode and SDK
ownership stays unchanged. Codex CLI is installed separately from the desktop
application, and its authentication and configuration remain local.

The yt-dlp selection matches only `yt-dlp_macos`, the standalone publisher
binary, rather than a Python wrapper. Mole's registry installs its scripts plus
the matching analyze/status helpers and links their resource directories.
Qualify `mo --version`, help, and a bounded read-only analysis before activation;
do not use Mole's self-update command on a Mise-managed installation.

```sh
dotfiles update --dry-run # preview Mise and Homebrew upgrades
dotfiles update           # upgrade Mise and Homebrew packages
mise outdated --global
mise doctor
```

The update command checks that the live Mise configuration matches the reviewed
source, then upgrades the selected Mise tools and Homebrew packages in that order.
It stops if a step fails; an earlier step may already have succeeded. It never
passes `--bump` or rewrites authored requests. Update a version range deliberately
in the source, validate it, and apply the config separately.

Homebrew upgrades all eligible installed formulae and casks, including packages
outside the Mise selection; its usual pinned and self-updating cask exclusions
apply. Homebrew may upgrade dependents, ask for input, or quit running apps during
cask upgrades. Automatic Homebrew cleanup is disabled for this command. Run
`dotfiles status` afterwards to refresh the startup banner. Normal chezmoi
application preserves unmanaged files and does not uninstall software.

`dotfiles status` reads Mise's installed metadata with `MISE_OFFLINE=1`, never by
running opted-in tools. It also reads `mise outdated --global --json` and
Homebrew metadata without installing anything. Missing versions and failed
checks are explicit. The opt-in startup banner keeps its
six-hour private cache, asynchronous refresh, shared lock and quiet default.
Its Python shim runs offline, so even a future Python update opt-in cannot make
status collection install software. Optional shell integration must also run
with `MISE_OFFLINE=1`; see [developer CLI tools](developer-cli-tools.md).

## git-slop and gh-steward distribution

The existing release assets are the Mise distribution source; no separate
package feed or publication job is needed. The global selection uses
`github:coreycoto/git-slop` and `github:coreycoto/gh-steward`. The latter sets
`bin = "gh-steward"` for its platform-named single-file release assets.
Git-slop's executable filter exposes only `git-slop`, retaining archive data.
Mise verifies GitHub asset digests and available artifact attestations.

Register the authored local extension once, after installing the binary:

```sh
cd ~/.local/share/dotfiles/gh-steward
gh extension install .
gh steward version --json
```

The directory contains only a wrapper, which forwards arguments and exit status
to `mise exec -- gh-steward`. Inspect an existing `steward` extension before
replacing it; do not force an unrelated installation. Authentication, access
permissions and approval of a signed mutation plan remain separate from binary
installation. The currently published gh-steward assets cover macOS and Linux;
Windows support requires separate publisher qualification.

See [Mise installation and verification](mise.md) for acquisition,
activation and recovery boundaries.

## Local Docker builds

Install Docker Desktop through Homebrew and launch it explicitly:

```sh
brew install --cask docker-desktop
docker desktop start --timeout 45
docker version
docker buildx version
docker info
```

Finish Docker Desktop's first-run setup if prompted. A working client alone
does not establish that the engine is ready. Keep Docker Desktop running while
project pre-push checks build images. The project owns its Dockerfiles, target
platforms, build commands, and hooks. Docker images, containers, credentials,
contexts, settings, and VM disks stay outside this repository; no Docker user
configuration is managed. Startup never starts Docker or installs software.
See [Homebrew's Docker Desktop cask](https://formulae.brew.sh/cask/docker-desktop)
and [Docker's Mac installation guide](https://docs.docker.com/desktop/setup/install/mac-install/).
