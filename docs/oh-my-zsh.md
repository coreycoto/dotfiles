# Oh My Zsh installation and maintenance

The dotfiles source owns the desired upstream revision in
`tools/oh-my-zsh.json`. Git installs it explicitly; chezmoi and shell startup
only manage the shell preferences. The reviewed pin is
[`60c9a7a839b790cd905d0fd4419435124fd1bdc0`](https://github.com/ohmyzsh/ohmyzsh/commit/60c9a7a839b790cd905d0fd4419435124fd1bdc0),
selected for this configuration. Installation checks cover the entry point,
disabled update path, selected plugin/theme layout and license. This pin does
not establish a security audit of every upstream plugin.

Upstream supports [manual installation](https://github.com/ohmyzsh/ohmyzsh#manual-installation).
This helper fetches exactly that commit, verifies its identity, checks out a
detached HEAD, and checks the files used by this configuration. It never runs
`tools/install.sh`, changes the login shell, writes `.zshrc`, or copies a
downloaded checkout into this repository. Git hooks and Git template hooks are
disabled during installation. The fetched tree retains upstream's
[MIT license](https://github.com/ohmyzsh/ohmyzsh/blob/60c9a7a839b790cd905d0fd4419435124fd1bdc0/LICENSE.txt).

## Fresh machine

Install Git, Zsh and Python explicitly first. On macOS, use the selected Apple
developer tools for Git/Zsh and the Python selected by mise. From the reviewed
dotfiles checkout, preview the destination, then install after reviewing it:

```sh
python3 scripts/oh-my-zsh.py --destination "$HOME/.oh-my-zsh"
python3 scripts/oh-my-zsh.py --destination "$HOME/.oh-my-zsh" --apply
```

Only `--apply` contacts the network or creates directories. Without
`--destination`, the helper uses the exported `ZSH` value, or
`~/.oh-my-zsh` if unset. It does not execute local shell options to find a path;
pass the path explicitly if your override is not exported. The destination
must be absolute, outside this repository, and absent. A clean checkout at
the same pin is a no-op; untracked custom files are retained. Different
revisions, tracked edits, non-Git directories and symlink targets are refused.
Failures before installation leave no partially installed target.

Preview, back up and apply dotfiles through the normal README procedure, then
open a second terminal. Keep the original terminal available during validation:

```zsh
git -C "$ZSH" rev-parse HEAD
print -r -- "$ZSH_THEME ${plugins[*]}"
zstyle -s ':omz:update' mode update_mode
print -r -- "$update_mode"
```

Expect the pinned revision, `robbyrussell git brew`, and `disabled`, unless
you deliberately selected a different theme or enabled `dotenv`. Verify normal
completion and entering/leaving a project. Before Oh My Zsh installation, the
managed shell already provides a basic prompt and Zsh completion. Neither
opening a shell nor `chezmoi apply` installs or upgrades Oh My Zsh.

## Existing installation and updates

Keep an existing installation intact. Its `custom/` directory can contain
authored plugins, themes and shell code. Review tracked modifications as well;
the installer does not move, overwrite or delete them. For migration or a pin
update, install into a new revision directory:

```sh
revision=$(python3 -c 'import json; print(json.load(open("tools/oh-my-zsh.json"))["revision"])')
python3 scripts/oh-my-zsh.py \
  --destination "$HOME/.local/share/oh-my-zsh/revisions/$revision"
# Review the preview, then repeat the command with --apply.
```

Before switching, back up `~/.config/zsh/options.local.zsh` outside Git with
restrictive permissions. If absent, record that fact. The general dotfiles
backup helper covers managed files; it does not back up this unmanaged overlay
or installed software. Keep the entire previous Oh My Zsh tree as the recovery
copy, including its custom files. Review the backup for private values.

Set `ZSH` to the new absolute path in that early local options file. Preserve
your existing `ZSH_THEME`, `ZSH_CACHE_DIR` and `ZSH_CUSTOM` choices. If custom
files currently live under the old checkout's `custom/`, set `ZSH_CUSTOM` to
that old absolute directory before switching `ZSH`; it remains the owner of
those files. Custom code can override upstream behavior, so review it on each
machine. A template example is:

```zsh
# Replace these placeholders with your reviewed paths.
ZSH="$HOME/.local/share/oh-my-zsh/revisions/REVIEWED_COMMIT"
ZSH_CUSTOM="$HOME/.oh-my-zsh/custom"
# Retain the existing theme selection here.
```

Validate a new shell and the revision before using it for normal work. Do not
use `omz update`, upstream's upgrade script, or `git pull` to advance this
checkout: those operations follow an upstream branch instead of the dotfiles
pin. For maintenance, review a specific upstream commit and the diff from
the current pin, update `tools/oh-my-zsh.json` and this provenance note, run
`./scripts/check`, and repeat the disposable-home real-upstream smoke described
below. Only then explicitly install that revision and switch the local path.
Do not delete the old tree as part of this workflow.

## Rollback and validation

To roll back a migration/update, restore the saved local options file (or
remove only the entries you added if it was absent), point `ZSH` at the previous
tree, and open another shell. Existing sessions continue using their loaded
configuration. Leave the new tree in place until any authored files are
reviewed separately.

For a fresh installation rollback, move the newly installed tree to a reviewed
recovery location outside Git and open another shell. With the default target
absent, the managed configuration uses the fallback prompt again. Preserve
custom code and caches rather than running upstream's uninstall script, which
can also replace shell configuration.

`./scripts/check` uses local Git fixtures and disposable homes to test preview,
installation, repeat application, refusal of existing/edited targets, local
overrides, the fallback prompt, and rollback without network access. Downloaded
dependencies remain outside the source tree. After a pin change, additionally
apply dotfiles and install the real pin into a disposable home with isolated
chezmoi configuration, state and caches. Start Zsh with `ZDOTDIR` pointing there,
verify the selected plugins/theme and disabled update style, then move that
temporary checkout aside and verify the fallback shell. This integration
smoke is an explicit network action; ordinary tests never use your live home.
