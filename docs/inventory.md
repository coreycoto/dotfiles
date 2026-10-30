# Inventory and scope

Managed files use an explicit allowlist. `manifest.json` maps every
managed source file to its home-directory target. Validation compares that
list with both source files and chezmoi's actual managed files.
The `.codex` allowlist covers only `AGENTS.md`, `autonomy-policy.md` and
`preferences.toml`; disposable-home tests enforce it and preserve unmanaged
machine state during repeated application.

| Source | Treatment |
|---|---|
| `.zshrc`, `.zprofile`, `.profile` | Refactor into entry points and five Zsh modules |
| `.gitconfig` | Keep shared preferences; move identity, signing, and application settings into an unmanaged local include |
| `.gitignore_global` | Manage the authored global ignore rules |
| `.config/git/ignore` | Unmanaged; preserve any local rules |
| Oh My Zsh and Bun installations | Reference existing installations; install Oh My Zsh explicitly from `tools/oh-my-zsh.json`; do not vendor or import downloaded trees |
| Homebrew packages | Retain desktop applications and native dependency stacks; do not reproduce every installed package or automatically remove existing formulae |
| Docker Desktop | Declare the Homebrew cask for local image builds; keep application settings, credentials, contexts, images, containers, and VM data local |
| mise configuration | Manage exact Node/Python/Rust defaults, Bun 1.x, global CLI requests and update checks every 6 hours; binaries, lock state and caches stay outside Git |
| uv configuration | Manage interpreter ownership policy; preserve existing cached Python and virtual environments |
| Global CLIs | Mise owns installations and version requests; use `dotfiles` for explicit maintenance; do not import generated installations |
| Project version selectors | Project source remains authoritative; private machine-local mappings stay outside this repo |
| Portless | Project-owned installation and [documentation only](portless.md); no portable user preferences selected; exclude all generated proxy state and certificates |
| GnuPG preferences | [Default preferences and local use](gnupg.md); no managed `gpg.conf` or `gpg-agent.conf`; keys, keyrings, trust, sockets, and backups remain local |
| SwiftPM package collections | [Toolchain and collection guidance](swiftpm.md); retain local source selections and tool-generated compatibility symlinks; do not import cache, credentials, or security state |
| Rustup and Cargo | Mise owns isolated homes; [toolchain and local configuration guidance](rust.md) preserves other installations and authored settings |
| SSH | Manage only a private `config` with a [local overlay and provisioning guide](ssh.md); retain all identities, keys, agents, and known hosts outside Git |
| VS Code | Manage two authored selection files; [explicitly merge portable preferences and install eight pinned extensions](vscode.md); retain unrelated preferences, keybindings, launch state, authentication, downloaded extensions, and databases locally |
| Authored `.agents/skills` | Manage only dotfiles-maintenance and personal global-cli-tools with their declared supporting files; portable tool guidance belongs to Agent Plugins; preserve other installed skills and generated state |
| `.codex` personal instructions and defaults | Render the canonical autonomy policy into global instructions; explicitly merge allowlisted model, built-in workspace access, feature, memory and desktop preferences plus a short reviewer hint through native Codex; keep concrete permission grants and host state local; purpose-specific routing belongs to publisher-owned agents |
| Personal `.agents/plugins/marketplace.json` | Manage the catalog template; preserve host-local entries in a private overlay |
| Private plugin sources | Keep catalog URLs, pins and selected versions in unmanaged `~/.config/dotfiles/agent-plugin-sources.local.json`; append validated optional entries without replacing public catalog selections |
| Shared agent plugins | Declare exact publisher revisions and selected versions; `dotfiles-plugins` pins native Git catalogs, verifies package bytes against publisher projections and installs only missing or changed versions; generated assets stay outside Git |
| Installed third-party skills | Record their provenance limits and qualification procedure; retain installed trees outside Git |
| Personal command-rule migration | Stage reviewed restrictions under `.config/dotfiles/codex-rules`; preview ownership and drift without changing active `.codex/rules`, remembered approvals or hook trust |
| Agent authentication, main config state, caches, sessions and databases | Keep local and preserve during repeated application |
| `.claude`, other agent directories | Unmanaged; any portable preferences or authored instructions require individual review |
| Other editors and `.config` applications | Unmanaged; add reviewed authored files individually |
| Apple Terminal | Exclude application profiles, themes and preferences; retain the portable shell configuration only |
| Credentials, SSH/GPG private keys, cloud authentication | Remain outside Git |
| Histories, sessions, caches, logs, databases, worktrees, binaries | Remain outside the dotfiles repository |
| Old backup files and apparently unused applications | Cleanup is deferred; age or filename is not evidence that a file is disposable |

Before adding another application, identify which files are authored
configuration, which contain credentials or personal information, which are
generated, and whether any paths are symlinks to shared configuration. Import
only reviewed source. Prefer documenting install commands for third-party
skills and plugins over copying their installed caches.

This inventory defines source scope; it is not an audit of every hidden
directory. Applying the managed files does not establish authentication or
change installed software.

Mise owns the global CLI selection. Explicit launchers preview/install
or upgrade from the reviewed checkout; the status helper reads metadata without
running tools. The local `gh-steward` extension wrapper is an explicitly managed
authored file, not a binary or an entire application directory.
