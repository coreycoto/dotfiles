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

## Agent discovery

The authored [developer-cli-tools skill](../home/dot_agents/skills/developer-cli-tools/SKILL.md)
and its focused tool references are managed through the explicit manifest.
Reviewed chezmoi application places the declared skill files under
`~/.agents/skills/developer-cli-tools`, the user skill location supported by
Codex. Invoke it as `$developer-cli-tools` or let its description match a tool
selection task. Start a new Codex session after application and check that the
skill is listed before relying on discovery. Another agent client must support
this skill location or receive an explicit path to `SKILL.md`; installing these
dotfiles locally does not install skills in a cloud environment.

The skill is owned here, rather than copied from an installed third-party skill
tree. Other skills, tool binaries, navigation history, and generated caches
remain outside this repo's managed selection. Review the normal chezmoi diff
and backup procedure before applying; this PR itself does not activate files
or install software on the current machine.

The [agent tool skill catalog](agent-tool-skills.md) covers runtime ownership,
dotfiles maintenance, repository checks, and GitHub operations as well.

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
