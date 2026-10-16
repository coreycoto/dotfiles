export ZSH="${ZSH:-$HOME/.oh-my-zsh}"
export ZSH_CACHE_DIR="${ZSH_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/oh-my-zsh}"
mkdir -p "$ZSH_CACHE_DIR/completions"

# Maintenance is explicit; opening a shell must not start an update.
zstyle ':omz:update' mode disabled
ZSH_THEME="${ZSH_THEME:-robbyrussell}"
plugins=(git brew)
if [[ "${DOTFILES_ENABLE_DOTENV:-0}" == 1 ]]; then
  plugins+=(dotenv)
fi

if [[ -r "$ZSH/oh-my-zsh.sh" ]]; then
  source "$ZSH/oh-my-zsh.sh"
else
  # A fresh machine can open a usable shell before installing Oh My Zsh.
  PROMPT='%F{green}%~%f %# '
  autoload -Uz compinit
  compinit -d "$ZSH_CACHE_DIR/.zcompdump"
fi

# The OMZ Bun plugin regenerates completions in a background process on every
# startup. Source Bun's installed completion file instead.
if [[ -r "$BUN_INSTALL/_bun" ]]; then
  source "$BUN_INSTALL/_bun"
fi
return 0
