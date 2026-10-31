---
name: global-cli-tools
description: Inspect or maintain this dotfiles setup's personal Mise global CLI declarations, update preferences and wrappers while preserving project pins.
---

# Personal global CLI preferences

Use this for the personal tool declarations and wrappers owned by these
dotfiles. Read the reviewed checkout's `docs/tool-ownership.md` and
`docs/mise.md`; executable versions and supported host selections live in the
consumer configuration. Do not impose the Mac setup on a cloud development VM.

The dotfiles own global requests in `~/.config/mise/config.toml`.
`dotfiles status` checks Homebrew and Mise for updates without installing them.
`dotfiles install --dry-run` previews installation, and `dotfiles update --dry-run`
previews Mise and Homebrew upgrades. `dotfiles update` covers eligible installed
Homebrew formulae and casks as well as the selected Mise tools. Run either
command only when the corresponding operation is authorized. Selected global
CLIs opt into command-triggered update checks every six hours; project
pins still win. Inspect current configuration before relying on that schedule.
Keep status checks offline with automatic installation disabled, and preserve
existing recovery installations unless their removal is separately requested.

For portable browser, Turbo, Vercel or Neon task guidance, use the installed
Product Development workflow and its conditional tool references. Those
references also cover search, runtime/dependency selection and repository checks
in local or cloud environments. This personal skill owns neither provider
authorization nor generic execution procedures. A compatible global binary can
be a fallback; a global update is not a project dependency upgrade.
