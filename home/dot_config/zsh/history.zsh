# Keep the existing history location; history itself is never versioned.
HISTFILE="${ZDOTDIR:-$HOME}/.zsh_history"
HISTSIZE=20000
SAVEHIST=20000
setopt share_history hist_ignore_all_dups hist_reduce_blanks hist_verify extended_glob
