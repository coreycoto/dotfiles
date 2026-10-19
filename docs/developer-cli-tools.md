# Developer CLI tools

The Mise config declares ripgrep, fd, fzf, zoxide, and bat as native tools.
Install them explicitly from a reviewed checkout with the normal command:

```sh
dotfiles-tools --apply
```

| Task | Tool | Agent use |
|---|---|---|
| Search contents | [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) | Scoped paths, literal or regex matching, explicit line numbers |
| Find files | [fd](https://github.com/sharkdp/fd) | Discover candidates before reading contents |
| Select candidates | [fzf](https://github.com/junegunn/fzf) | `--filter` with explicit stdin for unattended fuzzy discovery |
| Navigate remembered directories | [zoxide](https://github.com/ajeetdsouza/zoxide) | Prefer explicit checkout paths for reproducible work |
| Preview files | [bat](https://github.com/sharkdp/bat) | Disable paging/color and select a bounded range |

`fd` complements ripgrep for filename discovery and is part of the standard
Mise selection. Use `rg --files` or a scoped `find` when it is unavailable. These tools supplement standard
commands without replacing `grep`, `find`, `cd`, or `cat` with global aliases.

## Agent guidance

Portable search and navigation guidance now belongs to Product Development's
existing `understand-codebase` and `engineering-workflow` procedures in Agent
Plugins 0.10.5. The contained references cover scoped ripgrep/fd searches,
unattended fzf selection, bounded previews and explicit checkout identity.

Dotfiles continues to declare personal global binary versions and shell
preferences. It no longer distributes the standalone `developer-cli-tools`
skill. Existing home copies remain until replacement installation and discovery
have been verified and a scoped retirement is requested. Other installed skills,
tool binaries, navigation history and generated caches remain outside the
managed selection. See [guidance ownership](agent-tool-skills.md).

## Additional standalone tools

The same Mise selection owns actionlint, cargo-deny, shfmt, SwiftFormat,
SwiftLint, Tokei, Codex CLI, Pandoc, yt-dlp and Mole. Use project scripts and
project-pinned versions where provided; these globals are personal fallbacks.
Tokei keeps JSON/CBOR/YAML support through its Cargo `all` feature. Swift tools,
Mole and the standalone yt-dlp asset are selected on macOS. See
[tool ownership](tool-ownership.md) for backend choices and update behavior.

Mole maintenance operations require their own explicit scope. Prefer read-only
inspection when assessing storage; installation does not authorize cleanup.

## Optional Zsh integration

After installation, add only the integrations you want to the unmanaged
`~/.config/zsh/local.zsh` overlay:

```zsh
if command -v fzf >/dev/null 2>&1; then
  source <(MISE_OFFLINE=1 fzf --zsh)
fi
if command -v zoxide >/dev/null 2>&1; then
  eval "$(MISE_OFFLINE=1 zoxide init zsh)"
fi
```

This enables fzf key bindings/completion and zoxide's `z`/`zi` functions in
interactive shells. The shared shell configuration does not initialize either
tool automatically. Keep preferences and zoxide's visit database local; review
any key-binding conflict with an existing shell plugin before enabling it.
