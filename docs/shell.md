# Shell configuration


- `.zprofile` handles Homebrew's login environment and user-installed CLI paths.
- `.zshrc` loads interactive modules from `~/.config/zsh` in an explicit order.
- Project bins take precedence while inside the project and are removed when
  you leave it. Their order is `node_modules/.bin`, `bun_modules/.bin`,
  `.bun/bin`, `.bin`, then `bin`.
- Global PATH precedence is Antigravity, `~/.local/bin`, mise shims, Bun global packages,
  Bun itself, Apple Silicon Homebrew, then Intel/local installation paths.
  Only existing directories are added; inherited paths remain after these.
- Both `.profile` and `.zprofile` retain Docker Desktop's per-user CLI location
  at `$HOME/.docker/bin` when that directory exists. They append it after
  existing PATH entries, keep an inherited entry in place, and avoid duplicates
  when sourced repeatedly. Chezmoi owns this portable setup; Docker settings,
  credentials, contexts and installed CLI files remain local.
- Oh My Zsh uses the existing installation when available, with the
  `robbyrussell` theme and `git` and `brew` plugins. Bun completions come from
  the installed `$BUN_INSTALL/_bun` file, avoiding the Bun plugin's background
  regeneration at startup. A fresh machine
  gets a basic prompt and Zsh completions if Oh My Zsh is absent.
- Oh My Zsh automatic updates are disabled. Use the preview-by-default
  `scripts/oh-my-zsh.py` for an explicit pinned installation; follow
  [installation, updates and rollback](oh-my-zsh.md) for fresh machines
  and existing customizations.
- The `dotenv` plugin is opt-in through `DOTFILES_ENABLE_DOTENV=1` in the early
  local options file because it loads project environment files.
- `dotfiles status` checks Homebrew and Mise-selected versions and available
  updates without installing anything. It refreshes the startup banner cache.
  The startup banner remains quiet and offline except for its detached metadata
  refresh.
- `dotfiles install` installs the authored Mise selection. `dotfiles update`
  upgrades that selection within existing requests and upgrades Homebrew
  formulae and casks. Add `--dry-run` to preview either command.
  `dotfiles check` runs the checkout's validation suite in a disposable home.
  `dotfiles --help` lists the commands.
- Existing history location and settings are retained; history is never
  committed. The OS continues to determine the login shell's `SHELL` value.

This layout uses the default `~/.config/zsh` location. A full change to
`ZDOTDIR` or custom `XDG_CONFIG_HOME` requires separate configuration and testing.

## Optional startup status

To restore the version banner and available-update notices in new terminals,
add this preference to `~/.config/zsh/options.local.zsh`:

```zsh
DOTFILES_TOOL_STATUS_ON_STARTUP=1
```

Run `dotfiles status` once to populate the cache. New terminals display
that cached banner immediately. Results older than six hours refresh in the
background. In an interactive terminal, a small `⠋ tools` animation appears
below the editing line, becomes `✓ tools` when the cache is refreshed (or
`! tools` if refreshing fails), then clears after 1.5 seconds. It pauses while
a command runs, leaves the input and prompt theme intact, and stays silent in
captured output or dumb terminals. The next terminal displays the refreshed
results. A shared lock prevents duplicate checks when several terminals open
together. Startup never waits for version commands or network requests.

`DOTFILES_TOOL_STATUS_TTL` overrides the six-hour lifetime in seconds. Results
live under `${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/tool-status`, outside Git.
An offline or failed check is displayed as unavailable rather than up to date.
Homebrew checks refresh package API metadata without upgrading Homebrew itself;
structured package data is read separately from download progress. Warnings,
failed checks, and invalid metadata remain unavailable.
Third-party taps retain their locally installed metadata until you explicitly
run `brew update`. Mise tool versions come from `mise ls --current --json`
with offline mode enabled. Update metadata comes from `mise outdated --global
--json`; neither command launches a CLI or installs a version. Other managers
and self-updating apps are outside this banner's scope. The startup banner remains disabled by default.

## Verification

`./scripts/check` runs the full suite locally and in CI. CI runs for pull
requests, pushes to `main`, and manual dispatch, with a five-minute job timeout.
Each of the three real-terminal animation tests runs in a fresh Python worker
with a 30-second deadline. A timeout requests a signal-based Python stack dump,
retains captured terminal output and owned-process details, and kills the
worker and its observed descendant process groups after a short diagnostic
grace period. Ordinary test failures retain their traceback and terminal output.
Worker success, failure and timeout cleanup have independent fixture tests.
