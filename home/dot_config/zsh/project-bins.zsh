autoload -Uz add-zsh-hook
typeset -ga _dotfiles_project_paths

refresh_project_bins() {
  local entry previous dir keep
  local -a retained candidates
  retained=()

  # Compare literal paths so spaces and glob characters in names are safe.
  for entry in "${path[@]}"; do
    keep=1
    for previous in "${_dotfiles_project_paths[@]}"; do
      if [[ "$entry" == "$previous" ]]; then
        keep=0
        break
      fi
    done
    (( keep )) && retained+=("$entry")
  done

  candidates=(
    "$PWD/node_modules/.bin"
    "$PWD/bun_modules/.bin"
    "$PWD/.bun/bin"
    "$PWD/.bin"
    "$PWD/bin"
  )
  _dotfiles_project_paths=()
  for dir in "${candidates[@]}"; do
    [[ -d "$dir" ]] && _dotfiles_project_paths+=("$dir")
  done
  path=("${_dotfiles_project_paths[@]}" "${retained[@]}")
  return 0
}

# Also stay idempotent when the configuration is re-sourced in a live shell.
add-zsh-hook -d chpwd refresh_project_bins
add-zsh-hook chpwd refresh_project_bins
refresh_project_bins
