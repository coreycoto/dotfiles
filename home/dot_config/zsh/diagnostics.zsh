# Only the optional startup banner uses the cache. Manual checks stay explicit.
_dotfiles_tool_status_collect() (
  emulate -L zsh
  setopt extendedglob pipefail
  # A shared cache describes the home-level tools, not a project's .bin files.
  builtin cd -- "$HOME" || return 1
  (( $+functions[refresh_project_bins] )) && refresh_project_bins
  local updates=${1:-0} output version name row
  local brew_version='' brew_notice=''
  local -a outdated brew_rows
  local -x HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ANALYTICS=1
  local -x HOMEBREW_NO_INSTALL_CLEANUP=1 VERCEL_TELEMETRY_DISABLED=1
  # Python itself may be a shim. Status collection must never update any tool.
  local -x MISE_OFFLINE=1 MISE_AUTO_INSTALL=false MISE_EXEC_AUTO_INSTALL=false
  local -x MISE_NOT_FOUND_AUTO_INSTALL=false
  if (( $+commands[brew] )); then
    brew_version="$(command brew --version 2>/dev/null | awk 'NR == 1 { print $2 }')"
    if (( updates )); then
      # Refresh package metadata without upgrading Homebrew or any packages.
      local -x HOMEBREW_FORCE_API_AUTO_UPDATE=1
      local brew_helper="$HOME/.local/bin/dotfiles-brew-updates"
      if [[ -x "$brew_helper" ]] && (( $+commands[python3] )) && \
        output="$(command python3 "$brew_helper" 2>/dev/null)"; then
        [[ -n "$output" ]] && brew_rows=("${(@f)output}")
        for row in "${brew_rows[@]}"; do
          outdated+=("${row%%:*}")
        done
        if (( ${#outdated} )); then
          brew_notice=" (${#outdated} package updates available)"
        fi
      else
        brew_notice=' (update check unavailable)'
      fi
    fi
  fi

  print 'Tool status:'
  for name version in Homebrew "$brew_version"; do
    # Version strings and cached package names are data, never shell source.
    [[ -n "$version" && "$version" == [a-zA-Z0-9+._-]## ]] || continue
    case "$name" in
      Homebrew) output=$brew_notice ;;
    esac
    printf '  %-13s v%s%s\n' "$name" "$version" "$output"
    if [[ "$name" == Homebrew ]] && (( ${#brew_rows} )); then
      printf '    %s\n' "${brew_rows[@]}"
    fi
  done
  local helper="$HOME/.local/bin/dotfiles-mise-status"
  if [[ -x "$helper" ]] && (( $+commands[python3] )); then
    local -a args
    (( updates )) && args=(--updates)
    command python3 "$helper" "${args[@]}" 2>/dev/null || print '  Mise tools: status unavailable'
  fi
)

_dotfiles_tool_status_cache_fresh() {
  emulate -L zsh
  zmodload zsh/datetime || return 1
  zmodload zsh/stat || return 1
  local cache_file=$1 ttl=${DOTFILES_TOOL_STATUS_TTL:-21600}
  local -A cache_stat
  [[ "$ttl" == <-> ]] || ttl=21600
  [[ -f "$cache_file" && ! -L "$cache_file" ]] || return 1
  zstat -H cache_stat -- "$cache_file" 2>/dev/null || return 1
  (( EPOCHSECONDS >= cache_stat[mtime] && EPOCHSECONDS - cache_stat[mtime] < ttl ))
}

_dotfiles_tool_status_refresh() (
  emulate -L zsh
  umask 077
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/tool-status"
  local cache_file="$cache_dir/status-v2.txt" temp_file lock_fd lock_timeout=0
  [[ ! -L "$cache_dir" ]] || return 1
  command mkdir -p -- "$cache_dir" || return 1
  zmodload zsh/system || return 1
  [[ ! -L "$cache_dir/refresh.lock" ]] || return 1
  : >> "$cache_dir/refresh.lock" || return 1
  # Kernel-managed locks also release when a worker exits unexpectedly.
  # Automatic workers can wait off the prompt, then reuse the completed cache.
  [[ "${1:-}" == automatic ]] && lock_timeout=75
  zsystem flock -t "$lock_timeout" -f lock_fd "$cache_dir/refresh.lock" 2>/dev/null || return 75
  {
    [[ "${1:-}" == automatic ]] && _dotfiles_tool_status_cache_fresh "$cache_file" && return 0
    temp_file="$(command mktemp "$cache_dir/status.XXXXXXXX")" || return 1
    _dotfiles_tool_status_collect 1 > "$temp_file" || return 1
    command mv -f -- "$temp_file" "$cache_file" || return 1
  } always {
    [[ -n "$temp_file" ]] && command rm -f -- "$temp_file"
    zsystem flock -u "$lock_fd"
  }
)

_dotfiles_tool_status_print_cache() {
  emulate -L zsh
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Also quiet snapshots created before the notice format changed.
    line=${line%" (no update available)"}
    line=${line%" (no updates available)"}
    print -r -- "$line"
  done < "$1"
}

# Only this pipe carries animation events. Background checks never write to a tty.
_dotfiles_tool_status_events() (
  emulate -L zsh
  zmodload zsh/datetime || return 1
  zmodload zsh/zselect || return 1
  local result_fd result=1 deadline=$(( EPOCHSECONDS + 90 ))
  exec {result_fd}< <(
    _dotfiles_tool_status_refresh automatic </dev/null >/dev/null 2>&1
    print -r -- $?
  ) || return 1
  while (( EPOCHSECONDS < deadline )); do
    if zselect -t 15 -r "$result_fd"; then
      IFS= read -r -u "$result_fd" result || result=1
      break
    fi
    print -r -- running || return
  done
  exec {result_fd}<&-
  if [[ "$result" == 0 ]]; then
    print -r -- complete || return
  else
    print -r -- failed || return
  fi
  zselect -t 150
  print -r -- clear
)

_dotfiles_tool_status_indicator() {
  emulate -L zsh
  local fd=$1 event next eof=0
  # Coalesce queued ticks after a command: never replay old animation frames.
  while true; do
    IFS= read -r -u "$fd" next || { eof=1; break; }
    event=$next
    zselect -t 0 -r "$fd" || break
  done
  if (( eof )) || [[ "$event" == clear ]]; then
    zle -F "$fd"
    exec {fd}<&-
    unset _DOTFILES_TOOL_STATUS_FD _DOTFILES_TOOL_STATUS_FRAME
    zle -M ''
    return 0
  fi
  case "$event" in
    running)
      local -a frames=( '⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏' )
      typeset -g _DOTFILES_TOOL_STATUS_FRAME=$(( ${_DOTFILES_TOOL_STATUS_FRAME:-0} % ${#frames} + 1 ))
      zle -M "${frames[$_DOTFILES_TOOL_STATUS_FRAME]} tools"
      ;;
    complete) zle -M '✓ tools' ;;
    failed) zle -M '! tools' ;;
  esac
}

tool-status() {
  emulate -L zsh
  (( $# <= 1 )) || { print -u2 'Usage: tool-status [--updates]'; return 2; }
  case "${1:-}" in
    '') _dotfiles_tool_status_collect 0 ;;
    --updates)
      local result=0 cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/tool-status/status-v2.txt"
      _dotfiles_tool_status_refresh || result=$?
      if (( result )); then
        print -u2 'The update check could not run; another check may already be running.'
        return "$result"
      fi
      _dotfiles_tool_status_print_cache "$cache_file"
      ;;
    *) print -u2 'Usage: tool-status [--updates]'; return 2 ;;
  esac
}

# Preserve the old function name for existing manual use.
print_tool_status() {
  tool-status "$@"
}

_dotfiles_tool_status_startup() {
  emulate -L zsh
  unsetopt bgnice
  local cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/tool-status/status-v2.txt"
  if [[ -r "$cache_file" && -f "$cache_file" && ! -L "$cache_file" ]]; then
    _dotfiles_tool_status_print_cache "$cache_file"
    _dotfiles_tool_status_cache_fresh "$cache_file" && return 0
  fi
  # ZLE owns its message area and preserves the input buffer, cursor, and theme.
  # Captured output and dumb terminals stay silent, with no animation pipe.
  if [[ -t 0 && -t 1 && "${TERM:-dumb}" != dumb && -o zle ]] && \
    zmodload zsh/zselect 2>/dev/null && zmodload zsh/zle 2>/dev/null; then
    if exec {_DOTFILES_TOOL_STATUS_FD}< <( _dotfiles_tool_status_events </dev/null 2>/dev/null ); then
      zle -N _dotfiles_tool_status_indicator
      zle -F -w "$_DOTFILES_TOOL_STATUS_FD" _dotfiles_tool_status_indicator && return 0
      exec {_DOTFILES_TOOL_STATUS_FD}<&-
      unset _DOTFILES_TOOL_STATUS_FD
    fi
  fi
  ( _dotfiles_tool_status_refresh automatic ) </dev/null >/dev/null 2>&1 &!
}
