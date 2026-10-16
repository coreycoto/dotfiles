# First occurrence wins. Re-sourcing this module never duplicates entries.
typeset -U path fpath
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"

typeset -a _dotfiles_candidates _dotfiles_prepend
_dotfiles_candidates=(
  "$HOME/.antigravity/antigravity/bin"
  "$HOME/.local/bin"
  "${MISE_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/mise}/shims"
  "$BUN_INSTALL/install/global/node_modules/.bin"
  "$BUN_INSTALL/bin"
  /opt/homebrew/bin
  /opt/homebrew/sbin
  /usr/local/bin
  /usr/local/sbin
)
_dotfiles_prepend=()
for _dotfiles_dir in "${_dotfiles_candidates[@]}"; do
  [[ -d "$_dotfiles_dir" ]] && _dotfiles_prepend+=("$_dotfiles_dir")
done
path=("${_dotfiles_prepend[@]}" "${path[@]}")
export PATH
# Mise 2026.10.7 can relaunch a macOS symlink as the tool during auto-update.
# Supply its real entry point so updater subprocesses dispatch to Mise itself.
if [[ -x "$HOME/.local/bin/mise" ]]; then
  export __MISE_BIN="$HOME/.local/bin/mise"
fi
unset _dotfiles_candidates _dotfiles_prepend _dotfiles_dir
